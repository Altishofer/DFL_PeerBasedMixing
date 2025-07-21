import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from threading import Lock, Thread
from typing import List, Dict, Any

import aiohttp
import requests

from utils.config_store import ConfigStore


class MetricField(Enum):
    FRAGMENTS_RECEIVED = "fragments_received"
    FRAGMENTS_SENT = "fragments_sent"
    TOTAL_MSG_SENT = "total_sent"
    TOTAL_MSG_RECEIVED = "total_received"
    TOTAL_MBYTES_SENT = "total_mbytes_sent"
    TOTAL_MBYTES_RECEIVED = "total_mbytes_received"
    FORWARDED = "forwarded"
    SURB_REPLIED = "surb_replied"
    SURB_RECEIVED = "surb_received"
    ERRORS = "errors"
    CURRENT_ROUND = "current_round"
    TRAINING_ACCURACY = "accuracy"
    AGGREGATED_ACCURACY = "aggregated_accuracy"
    RESENT = "resent"
    ACTIVE_PEERS = "active_peers"
    COVERS_SENT = "covers_sent"
    COVERS_RECEIVED = "covers_received"
    OUT_INTERVAL = "out_interval"
    SENDING_COVERS = "sending_covers"
    SENDING_MESSAGES = "sending_messages"
    DELETED_CACHE_FOR_INACTIVE = "deleted_cache_for_inactive"
    ROUND_TIME = "round_time"
    UNACKED_MSG = "unacked_msg"
    RECEIVED_DUPLICATE_MSG = "received_duplicate_msg"
    AVG_RTT = "avg_rtt"
    LAST_RTT = "last_rtt"
    QUEUED_PACKAGES = "queued_packages"

    STAGE = "stage"
    """
      Training: 1,
      Local Aggregation: 2
      Broadcasting and Collection: 3
      Global Aggregation: 4
    """


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
        self._controller_url = controller_url
        self._host = host_name

        if controller_url:
            Thread(target=self._push_loop, daemon=True).start()

    def increment(self, field: MetricField, amount: int = 1):
        with self._data_lock:
            self._data[field] += amount

    def decrement(self, field: MetricField, amount: int = 1):
        with self._data_lock:
            if field in self._data:
                self._data[field] -= amount
                if self._data[field] < 0:
                    self._data[field] = 0

    def set(self, field: MetricField, value: int | str):
        with self._data_lock:
            self._data[field] = value

    def _flush_metrics(self):
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with self._data_lock:
            updates = [{
                "timestamp": timestamp,
                "field": field.value,
                "value": value,
                "node": self._host
            } for field, value in self._data.items()]
            self._change_log = deque(updates)

    def get_all(self) -> Dict[str, Any]:
        with self._data_lock:
            return {field.value: value for field, value in self._data.items()}

    def get_log(self) -> List[Dict[str, Any]]:
        with self._data_lock:
            return list(self._change_log)

    def _push_loop(self):
        while True:
            interval = ConfigStore.push_metric_interval
            self._flush_metrics()
            self._push_metrics()
            time.sleep(interval)

    def _push_metrics(self):
        try:
            with self._data_lock:
                if not self._change_log:
                    return
                payload = list(self._change_log)
            response = requests.post(
                f"{self._controller_url}/metrics/push",
                json=payload,
                timeout=ConfigStore.push_metric_interval
            )
            if response.status_code == 200:
                with self._data_lock:
                    self._change_log.clear()
            else:
                logging.warning(f"Push failed: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logging.warning(f"Push exception: {e}")

    async def wait_for_round(self, round_number: int):
        async with aiohttp.ClientSession() as session, session.get(f"{self._controller_url}/metrics/sse") as response:
            async for line in response.content:
                try:
                    if not line:
                        continue
                    decoded_line = line.decode("utf-8").strip()
                    if not decoded_line.startswith("data:"):
                        continue
                    data = json.loads(decoded_line[5:])
                    if any(row.get("field") == MetricField.CURRENT_ROUND.value and int(
                            row.get("value", 0)) >= round_number for row in data):
                        logging.info(f"Round {round_number} reached")
                        return
                except Exception as e:
                    logging.warning(f"Error processing line: {line}. Exception: {e}")
                    continue
