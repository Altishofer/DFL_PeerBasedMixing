import asyncio
import datetime
import msgpack
from pathlib import Path
from typing import List
from manager.config import settings
from manager.services.cache_service import cache_service
from manager.models.schemas import MetricPoint
from manager.utils.docker_utils import get_docker_client


class MetricsService:
    def __init__(self):
        self._running = False
        self._client = get_docker_client()

    async def start_collecting(self):
        if self._running:
            return

        self._running = True
        asyncio.create_task(self._collect_loop())

    async def stop_collecting(self):
        self._running = False

    async def _collect_loop(self):
        while self._running:
            metrics = await self._collect_metrics()
            if metrics:
                await self._store_metrics(metrics)
                await cache_service.add_metrics(metrics)
            await asyncio.sleep(settings.METRICS_INTERVAL)

    async def _collect_metrics(self) -> List[MetricPoint]:
        containers = self._client.containers.list()
        active_nodes = [c for c in containers if c.name.startswith("node_")]

        if not active_nodes:
            return []

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        metrics = []

        for container in active_nodes:
            try:
                stats = container.stats(stream=False)
                cpu = stats["cpu_stats"]["cpu_usage"]["total_usage"] / 10e9
                memory = round(stats["memory_stats"]["usage"] / (1024 * 1024), 2)

                metrics.extend([
                    MetricPoint(
                        timestamp=timestamp,
                        field="cpu_total_ns",
                        value=cpu,
                        node=container.name
                    ),
                    MetricPoint(
                        timestamp=timestamp,
                        field="memory_mb",
                        value=memory,
                        node=container.name
                    )
                ])
            except Exception as e:
                continue

        return metrics

    async def _store_metrics(self, metrics: List[MetricPoint]):
        if not metrics:
            return

        try:
            serialized = msgpack.packb([m.dict() for m in metrics])
            async with await asyncio.to_thread(open, settings.METRICS_FILE, "ab") as f:
                await f.write(serialized)
        except Exception as e:
            pass

    async def get_all_metrics(self) -> List[dict]:
        try:
            async with await asyncio.to_thread(open, settings.METRICS_FILE, "rb") as f:
                data = await f.read()
                return msgpack.unpackb(data)
        except FileNotFoundError:
            return []
        except Exception:
            return []


metrics_service = MetricsService()