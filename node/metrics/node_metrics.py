import asyncio
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
    AVG_MSG_PER_SECOND = "avg_msg_per_second"
    LAST_RTT = "last_rtt"
    QUEUED_PACKAGES = "queued_packages"
    SENDING_TIME = "sending_time"
    TOTAL_OUT_INTERVAL = "total_out_interval"

    STAGE = "stage"
    """
      Bootstrapping: 0,
      Training: 1,
      Local Evaluation: 2
      Broadcasting, Forwarding & Collection: 3
      Global Evalutation: 4
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
        self._start_time = 0

        if controller_url:
            Thread(target=self._push_loop, daemon=True).start()

    def increment(self, field: MetricField, amount: int = 1):
        if (field == MetricField.TOTAL_MSG_SENT and self._start_time == 0):
            self._start_time = time.time()
        with self._data_lock:
            self._data[field] += amount

    def decrement(self, field: MetricField, amount: int = 1):
        with self._data_lock:
            if field in self._data:
                self._data[field] -= amount
                if self._data[field] < 0:
                    self._data[field] = 0

    def set(self, field: MetricField, value: int | str | float):
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
            self.set_message_frequency()
            self._flush_metrics()
            self._push_metrics()
            time.sleep(ConfigStore.push_metric_interval)

    def set_message_frequency(self):
        elapsed_time = time.time() - self._start_time
        frequency = self._data[MetricField.TOTAL_MSG_SENT] / elapsed_time
        self.set(MetricField.AVG_MSG_PER_SECOND, frequency)

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
        async with aiohttp.ClientSession(read_bufsize=1024 * 1024) as session:
            async with session.get(f"{self._controller_url}/metrics/sse") as response:
                while True:
                    try:
                        async for line in response.content:
                            try:
                                if not line:
                                    continue
                                decoded_line = line.decode("utf-8").strip()
                                if not decoded_line.strip() or not decoded_line.startswith("data: "):
                                    continue
                                json_part = decoded_line.split("data: ", 1)[1]
                                data = json.loads(json_part)
                                for row in data:
                                    if row.get("field") == MetricField.CURRENT_ROUND.value:
                                        logging.debug(f"Received round: {row.get('value')}")
                                        if int(row.get("value", 0)) >= round_number:
                                            logging.info(f"Awaited round reached: {round_number}")
                                            return
                            except Exception as e:
                                logging.warning(f"Error processing line: {line}. Exception: {e}")
                                continue
                    except asyncio.TimeoutError:
                        logging.warning("Timeout while waiting for round metrics.")
                        continue
                    except ValueError as e:
                        logging.warning(f"ValueError while processing SSE data: {e}")
                        continue
