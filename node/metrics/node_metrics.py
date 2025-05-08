import asyncio
import httpx
from dataclasses import dataclass, asdict
from threading import Lock, Thread
from typing import List, Dict, Any
from datetime import datetime, timezone


@dataclass
class MetricData:
    msg_sent: int = 0
    payload_sent: int = 0
    msg_recv: int = 0
    errors: int = 0


class Metrics:
    _instance = None
    _lock = Lock()

    def __new__(cls, controller_url: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init(controller_url)
        return cls._instance

    def _init(self, controller_url: str = None):
        self._data = MetricData()
        self._data_lock = Lock()
        self._change_log: List[Dict[str, Any]] = []
        self._controller_url = controller_url
        if controller_url:
            Thread(target=self._start_background_loop, daemon=True).start()

    def _record_change(self, field: str, value: Any):
        self._change_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "field": field,
            "value": value
        })

    def increment(self, field: str, amount: int = 1):
        with self._data_lock:
            current = getattr(self._data, field)
            new_value = current + amount
            setattr(self._data, field, new_value)
            self._record_change(field, new_value)

    def set(self, field: str, value: Any):
        with self._data_lock:
            setattr(self._data, field, value)
            self._record_change(field, value)

    def get_all(self) -> Dict[str, Any]:
        with self._data_lock:
            return asdict(self._data)

    def get_log(self) -> List[Dict[str, Any]]:
        with self._data_lock:
            return list(self._change_log)

    def _start_background_loop(self):
        asyncio.run(self._push_loop())

    async def _push_loop(self):
        async with httpx.AsyncClient() as client:
            while True:
                await asyncio.sleep(1.0)
                data = self.get_log()
                if data and self._controller_url:
                    try:
                        await client.post(f"{self._controller_url}/metrics", json=data)
                    except Exception as e:
                        print(f"[ERROR] Failed to push metrics: {e}")
