import asyncio
import time
import logging
from collections import defaultdict
from typing import List, Tuple, Optional


class MessageCache:
    def __init__(self):
        # logging.debug("⚡️ MessageCache.__init__ called")
        self._cache = defaultdict(dict)
        self._timestamps = defaultdict(dict)
        self._inflight_count = 0
        self._lock = asyncio.Lock()

    async def add(self, seq: int, idx: int, message: bytes):
        async with self._lock:
            # logging.debug(f"⚡️ MessageCache.add called with seq={seq}, idx={idx}, size={len(message)}")
            self._cache[seq][idx] = message
            self._timestamps[seq][idx] = time.time()
            self._inflight_count += 1
            # logging.debug(f"⚡️ MessageCache.add -> inflight={self._inflight_count}")

    async def remove_acknowledged(self, seq: int, idx: int) -> Optional[float]:
        async with self._lock:
            # logging.debug(f"⚡️ MessageCache.remove_acknowledged called with seq={seq}, idx={idx}")
            start = self._timestamps.get(seq, {}).get(idx)

            if seq in self._cache and idx in self._cache[seq]:
                del self._cache[seq][idx]
                if not self._cache[seq]:
                    del self._cache[seq]

            if seq in self._timestamps and idx in self._timestamps[seq]:
                del self._timestamps[seq][idx]
                if not self._timestamps[seq]:
                    del self._timestamps[seq]

            self._inflight_count = max(self._inflight_count - 1, 0)
            # logging.debug(f"⚡️ MessageCache.remove_acknowledged -> timestamp={start}, inflight={self._inflight_count}")
            return start

    async def inflight(self) -> int:
        async with self._lock:
            # logging.debug(f"⚡️ MessageCache.inflight -> {self._inflight_count}")
            return self._inflight_count

    async def n_sequences(self) -> int:
        async with self._lock:
            count = len(self._cache)
            # logging.debug(f"⚡️ MessageCache.n_sequences -> {count}")
            return count

    async def n_fragments(self) -> int:
        async with self._lock:
            count = sum(len(frag_dict) for frag_dict in self._cache.values())
            # logging.debug(f"⚡️ MessageCache.n_fragments -> {count}")
            return count

    async def all(self) -> List[Tuple[int, int, bytes, float]]:
        async with self._lock:
            result = []
            for seq, idx_dict in self._cache.items():
                for idx, message in idx_dict.items():
                    timestamp = self._timestamps[seq][idx]
                    result.append((seq, idx, message, timestamp))
            # logging.debug(f"⚡️ MessageCache.all {len(result)} entries")
            return result

    async def update_sent_time(self, seq: int, idx: int):
        async with self._lock:
            exists_in_timestamps = seq in self._timestamps and idx in self._timestamps[seq]
            exists_in_cache = seq in self._cache and idx in self._cache[seq]
            if exists_in_timestamps and exists_in_cache:
                self._timestamps[seq][idx] = time.time()
                # logging.debug(f"⚡️ MessageCache.update_sent_time seq={seq}, idx={idx}")
            else:
                pass
                # logging.debug(f"⚡️ MessageCache.update_sent_time skipped (not found) seq={seq}, idx={idx}")
