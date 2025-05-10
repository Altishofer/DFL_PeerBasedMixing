from collections import deque
import asyncio
from typing import Deque, Any
from manager.config import settings


class CacheService:
    def __init__(self):
        self._metrics_cache: Deque[Any] = deque(maxlen=settings.MAX_METRICS_CACHE)
        self._status_cache = None
        self._lock = asyncio.Lock()

    async def add_metrics(self, metrics: list) -> None:
        async with self._lock:
            self._metrics_cache.extend(metrics)

    async def get_metrics(self) -> list:
        async with self._lock:
            return list(self._metrics_cache)

    async def clear_metrics(self) -> None:
        async with self._lock:
            self._metrics_cache.clear()

    async def set_status(self, status: list) -> None:
        async with self._lock:
            self._status_cache = status

    async def get_status(self) -> list:
        async with self._lock:
            return self._status_cache or []


cache_service = CacheService()