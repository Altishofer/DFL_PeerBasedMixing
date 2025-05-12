import random
import time
import requests
import logging
from threading import Lock, Thread
from typing import List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from collections import deque


class MetricField(Enum):
    MSG_SENT = "msg_sent"
    PAYLOAD_SENT = "payload_sent"
    MSG_RECV = "msg_recv"
    ERRORS = "errors"
    TIME_STAMP = "time_stamp"
    SURB_RECEIVED = "surb_received"
    FRAGMENT_RECEIVED = "fragment_received"
    BYTES_RECEIVED = "bytes_received"
    CURRENT_ROUND = "current_round"
    ACCURACY = "accuracy"
    FRAGMENT_RESENT = "fragment_resent"
    BYTES_SENT = "bytes_sent"
    FRAGMENTS_FORWARDED = "fragments_forwarded"


_metrics_instance = None

def init_metrics(controller_url: str, host_name: str):
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = Metrics(controller_url, host_name)
    return _metrics_instance

def metrics():
    if _metrics_instance is None:
        raise RuntimeError("Metrics not initialized. Call init_metrics() first.")
    return _metrics_instance


class Metrics:
    def __init__(self, controller_url: str, host_name: str):
        self._data: Dict[MetricField, int] = {field: 0 for field in MetricField}
        self._data_lock = Lock()
        self._change_log: deque = deque()
        self._metrics_buffer: Dict[MetricField, int] = {}
        self._controller_url = controller_url
        self._host = host_name

        if controller_url:
            Thread(target=self._push_loop, daemon=True).start()
            Thread(target=self._flush_buffer_loop, daemon=True).start()

    def increment(self, field: MetricField, amount: int = 1):
        with self._data_lock:
            self._data[field] += amount
            self._metrics_buffer[field] = max(self._metrics_buffer.get(field, 0), self._data[field])

    def set(self, field: MetricField, value: int):
        with self._data_lock:
            self._data[field] = value
            self._metrics_buffer[field] = max(self._metrics_buffer.get(field, value), value)

    def _flush_buffer_loop(self):
        interval = 3
        while True:
            start = time.monotonic()
            self._flush_metrics()
            elapsed = time.monotonic() - start
            time.sleep(max(0, interval - elapsed))

    def _flush_metrics(self):
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with self._data_lock:
            updates = [{
                "timestamp": timestamp,
                "field": field.value,
                "value": value,
                "node": self._host
            } for field, value in self._metrics_buffer.items()]
            self._change_log.extend(updates)
            self._metrics_buffer.clear()

    def get_all(self) -> Dict[str, Any]:
        with self._data_lock:
            return {field.value: value for field, value in self._data.items()}

    def get_log(self) -> List[Dict[str, Any]]:
        with self._data_lock:
            return list(self._change_log)

    def _push_loop(self):
        base_interval = 3
        while True:
            jitter = random.uniform(-0.1, 0.1)
            interval = base_interval + jitter
            start = time.monotonic()
            self._push_metrics()
            elapsed = time.monotonic() - start
            time.sleep(max(0, interval - elapsed))

    def _push_metrics(self):
        try:
            with self._data_lock:
                if not self._change_log:
                    return
                payload = list(self._change_log)
            response = requests.post(
                f"{self._controller_url}/metrics/push",
                json=payload,
                timeout=3
            )
            if response.status_code == 200:
                with self._data_lock:
                    self._change_log.clear()
            else:
                logging.warning(f"Push failed: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logging.warning(f"Push exception: {e}")
