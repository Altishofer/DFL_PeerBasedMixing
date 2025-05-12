import asyncio
import datetime
import msgpack
import logging
import time
from pathlib import Path
from typing import List, Callable, Coroutine, Any
from manager.config import settings
from manager.services.cache_service import cache_service
from manager.models.schemas import MetricPoint
from manager.utils.docker_utils import get_docker_client

logger = logging.getLogger(__name__)

class MetricsService:
    def __init__(self):
        self._running = False
        self._client = get_docker_client()
        self._write_queue = asyncio.Queue()
        self._writer_task = None

    async def start_collecting(self):
        if self._running:
            return

        self._running = True
        self._writer_task = asyncio.create_task(self._writer_loop())
        asyncio.create_task(self._collect_loop())

    async def stop_collecting(self):
        self._running = False
        if self._writer_task:
            self._writer_task.cancel()
            try:
                await self._writer_task
            except asyncio.CancelledError:
                logger.warning("Writer task was cancelled cleanly")
            self._writer_task = None

    async def _collect_loop(self):
        while self._running:
            try:
                metrics = await asyncio.to_thread(self._collect_metrics)
                if metrics:
                    self._write_queue.put_nowait(metrics)
                    await cache_service.add_metrics(metrics)
            except Exception as e:
                logger.error(f"Error during metric collection: {e}")
            await asyncio.sleep(settings.METRICS_INTERVAL)

    async def _writer_loop(self):
        while True:
            first_item = await self._write_queue.get()
            batch = [first_item]

            try:
                while True:
                    item = self._write_queue.get_nowait()
                    batch.append(item)
            except asyncio.QueueEmpty:
                pass

            try:
                start = time.perf_counter()
                flat_metrics = [m.model_dump() for metrics in batch for m in metrics]
                serialized = msgpack.packb(flat_metrics)
                await asyncio.to_thread(self._write_to_file, serialized)
                duration = (time.perf_counter() - start) * 1000
                logger.info(f"Wrote {len(flat_metrics)} metrics in {duration:.2f} ms")
            except Exception as e:
                logger.error(f"Failed to write metrics to file: {e}")

    def _write_to_file(self, serialized_data: bytes):
        with open(settings.METRICS_FILE, "ab") as f:
            f.write(serialized_data)

    async def reset_file(self):
        with open(settings.METRICS_FILE, "wb") as f:
            f.truncate(0)

    def _collect_metrics(self) -> List[MetricPoint]:
        try:
            containers = self._client.containers.list()
        except Exception as e:
            logger.error(f"Failed to list Docker containers: {e}")
            return []

        active_nodes = [c for c in containers if c.name.startswith("node_")]
        if not active_nodes:
            return []

        timestamp = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
        metrics = []

        for container in active_nodes:
            try:
                stats = container.stats(stream=False)
                cpu = stats["cpu_stats"]["cpu_usage"]["total_usage"] / 10e9
                memory = round(stats["memory_stats"]["usage"] / (1024 * 1024), 2)
                metrics.extend([
                    MetricPoint(timestamp=timestamp, field="cpu_total_ns", value=cpu, node=container.name),
                    MetricPoint(timestamp=timestamp, field="memory_mb", value=memory, node=container.name)
                ])
            except Exception as e:
                logger.warning(f"Failed to collect metrics from {container.name}: {e}")
                continue

        return metrics

    async def get_all_metrics(self) -> List[dict]:
        try:
            return await asyncio.to_thread(self._read_all_metrics)
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Failed to read metrics file: {e}")
            return []

    def _read_all_metrics(self) -> List[dict]:
        metrics = []
        with open(settings.METRICS_FILE, "rb") as f:
            unpacker = msgpack.Unpacker(f, raw=False)
            for batch in unpacker:
                for item in batch:
                    metrics.append(MetricPoint(**item).model_dump())
        return metrics

    async def enqueue_metrics(self, metrics: List[MetricPoint]):
        self._write_queue.put_nowait(metrics)

metrics_service = MetricsService()
