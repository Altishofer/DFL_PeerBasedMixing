import asyncio
from collections import deque
from typing import Deque

from manager.models.schemas import MetricPoint


class CacheService:
    def __init__(self):
        self._metrics_cache: Deque[MetricPoint] = deque()
        self._lock = asyncio.Lock()

    async def add_metrics(self, metrics: list) -> None:
        async with self._lock:
            self._metrics_cache.extend(metrics)

    async def pop_all_metrics(self) -> list:
        async with self._lock:
            items = list(self._metrics_cache)
            self._metrics_cache.clear()
            return items

    async def get_metrics(self) -> list:
        async with self._lock:
            return list(self._metrics_cache)

    async def clear_cache(self) -> None:
        async with self._lock:
            self._metrics_cache.clear()


cache_service = CacheService()
