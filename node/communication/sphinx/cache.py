import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List
import logging

from metrics.node_metrics import metrics, MetricField
from utils.exception_decorator import log_exceptions


@dataclass
class Fragment:
    surb_id: bytes
    surb_key_tuble: tuple
    target_node: int
    payload: bytes
    timestamp: datetime
    acked: bool


class Cache:

    def __init__(self):
        self.cache = {}
        self.out_counter = 0
        self.in_counter = 0

    @log_exceptions
    def new_fragment(self, surb_id: bytes, surb_key_tuple: tuple, target_node: int, payload: bytes):
        now = datetime.now(timezone.utc)
        fragment = Fragment(surb_id, surb_key_tuple, target_node, payload, now, False)
        self.cache[surb_id] = fragment
        self.out_counter += 1

    @log_exceptions
    def received_surb(self, surb_id):
        metrics().increment(MetricField.SURB_RECEIVED)
        self.cache[surb_id].acked = True
        self.in_counter += 1
        return self.cache[surb_id].surb_key_tuble

    @log_exceptions
    def delete_cache_for_node(self, target_node):
        to_delete = [surb_id for surb_id, fragment in self.cache.items() if fragment.target_node == target_node]
        for surb_id in to_delete:
            del self.cache[surb_id]
        logging.debug(f"Deleted {len(to_delete)} fragments for node {target_node}.")
        return len(to_delete)

    @log_exceptions
    def clear_acked_cache(self):
        to_delete = [surb_id for surb_id, fragment in self.cache.items() if fragment.acked]
        for surb_id in to_delete:
            del self.cache[surb_id]
        logging.debug(f"Cleared {len(to_delete)} acked fragments from cache.")
        return len(to_delete)

    @log_exceptions
    def get_older_than(self, seconds: float) -> List[Fragment]:
        # self.clear_acked_cache()
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        to_resend = [fragment for fragment in self.cache.values() if fragment.timestamp < cutoff and not fragment.acked]
        for fragment in to_resend:
            self.cache[fragment.surb_id].acked = True  # Mark as acked to prevent resending
        metrics().increment(MetricField.FRAGMENT_RESENT, len(to_resend))
        logging.info(f"{self.in_counter=}, {self.out_counter=}, {len(to_resend)=}, {len(self.cache)=}")
        return to_resend
