import random
import time
import requests
import logging
from threading import Lock, Thread
from typing import List, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class MetricField(Enum):
    MSG_SENT = "msg_sent"
    PAYLOAD_SENT = "payload_sent"
    MSG_RECV = "msg_recv"
    ERRORS = "errors"
    TIME_STAMP = "time_stamp"
    SURB_RECEIVED = "surb_received"
    FRAGMENT_RECEIVED = "fragment_received"
    BYTES_RECEIVED = "bytes_received"

    FRAGMENT_RESENT = "fragment_resent"
    BYTES_SENT = "bytes_sent"

    FRAGMENTS_FORWARDED = "fragments_forwarded"


_metrics_instance = None

def init_metrics(controller_url: str, host_name: str):
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = Metrics(controller_url=controller_url, host_name=host_name)
    return _metrics_instance

def metrics():
    if _metrics_instance is None:
        raise RuntimeError("Metrics not initialized. Call init_metrics() first.")
    return _metrics_instance


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
        self._data: Dict[MetricField, int] = {field: 0 for field in MetricField}
        self._data_lock = Lock()
        self._change_log: List[Dict[str, Any]] = []
        self._controller_url = controller_url
        self._host = host_name
        if controller_url:
            thread = Thread(target=self._push_loop, daemon=True)
            thread.start()

    def _record_change(self, field: MetricField, value: Any):
        self._change_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "field": field.value,
            "value": value,
            "node": self._host
        })

    def increment(self, field: MetricField, amount: int = 1):
        with self._data_lock:
            self._data[field] += amount
            self._record_change(field, self._data[field])

    def set(self, field: MetricField, value: int):
        with self._data_lock:
            self._data[field] = value
            self._record_change(field, value)

    def get_all(self) -> Dict[str, Any]:
        with self._data_lock:
            return {field.value: value for field, value in self._data.items()}

    def get_log(self) -> List[Dict[str, Any]]:
        with self._data_lock:
            return list(self._change_log)

    def _push_loop(self):
        while True:
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
