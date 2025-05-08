import random
import time
import requests
import logging
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

    def __new__(cls, controller_url: str, host_name: str):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init(controller_url, host_name)
        return cls._instance

    def _init(self, controller_url: str, host_name: str):
        self._data = MetricData()
        self._data_lock = Lock()
        self._change_log: List[Dict[str, Any]] = []
        self._controller_url = controller_url
        self._host = host_name
        if controller_url:
            thread = Thread(target=self._push_loop, daemon=True)
            thread.start()

    def _record_change(self, field: str, value: Any):
        self._change_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "field": field,
            "value": value,
            "node":self._host
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

    def _push_loop(self):
        while True:
            for field in ['msg_sent', 'payload_sent', 'msg_recv', 'errors']:
                amount = random.randint(1, 10)
                self.increment(field, amount)

            time.sleep(1.0)
            data = self.get_log()
            if not data:
                continue
            try:
                response = requests.post(f"{self._controller_url}/receive_metrics", json=data)
                if response.status_code == 200:
                    with self._data_lock:
                        self._change_log.clear()
                else:
                    logging.error(f"Push failed with status {response.status_code}: {response.text}")
            except Exception as e:
                logging.error(f"Exception during metrics push: {e}")

