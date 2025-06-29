import asyncio
import datetime
import logging
import csv
from typing import List, Any
from manager.config import settings
from manager.services.cache_service import cache_service
from manager.utils.docker_utils import get_docker_client
from manager.models.schemas import MetricPoint

logger = logging.getLogger(__name__)

class MetricsService:
    def __init__(self):
        self._running = False
        self._client = get_docker_client()
        self._write_queue = asyncio.Queue()

    async def start_collecting(self):
        if not self._running:
            self._running = True
            asyncio.create_task(self._collect_loop())

    async def stop_collecting(self):
        self._running = False

    async def _collect_loop(self):
        while self._running:
            try:
                metrics = await asyncio.to_thread(self._collect_metrics)
                if metrics:
                    await self.enqueue_metrics(metrics)
                    await cache_service.add_metrics(metrics)
            except Exception as e:
                logger.error(f"Error during metric collection: {e}")
            await asyncio.sleep(settings.METRICS_INTERVAL)

    def _collect_metrics(self) -> List[MetricPoint]:
        try:
            containers = self._client.containers.list()
            active_nodes = [c for c in containers if c.name.startswith("node_")]
        except Exception as e:
            logger.error(f"Failed to list Docker containers: {e}")
            return []

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        metrics = []
        for container in active_nodes:
            try:
                stats = container.stats(stream=False)
                metrics.append(
                    MetricPoint(
                        timestamp=timestamp,
                        field="cpu_total_ns",
                        value=stats["cpu_stats"]["cpu_usage"]["total_usage"] / 10e9,
                        node=container.name
                    )
                )
                metrics.append(
                    MetricPoint(
                        timestamp=timestamp,
                        field="memory_mb",
                        value=round(stats["memory_stats"]["usage"] / (1024 * 1024), 2),
                        node=container.name
                    )
                )
            except Exception:
                logger.warning(f"Failed to collect metrics from {container.name}")
        return metrics

    async def save_to_csv(self):
        try:
            if self._write_queue.empty():
                logger.info("No metrics to save.")
                return

            filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S_metrics.csv")
            with open(filename, mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["timestamp", "field", "value", "node"])

                while not self._write_queue.empty():
                    metrics = await self._write_queue.get()
                    for metric in metrics:
                        writer.writerow([metric.timestamp, metric.field, metric.value, metric.node])

        except Exception as e:
            logger.error(f"Failed to save metrics to CSV: {e}")

    async def enqueue_metrics(self, metrics: List[MetricPoint]):
        if not all(isinstance(metric, MetricPoint) for metric in metrics):
            raise ValueError("All items in the metrics list must be instances of MetricPoint.")
        for metric in metrics:
            self._write_queue.put_nowait(metric)

    async def get_all_metrics(self) -> list[Any]:
        return list(self._write_queue._queue)

metrics_service = MetricsService()
