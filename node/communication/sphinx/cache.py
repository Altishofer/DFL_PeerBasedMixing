import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List
import logging
import numpy as np
from utils.config_store import ConfigStore

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
    cover: bool


class Cache:

    def __init__(self):
        self.cache = {}
        self.out_counter = 0
        self.in_counter = 0
        self.rtts = []

    @log_exceptions
    def new_fragment(self, surb_id: bytes, surb_key_tuple: tuple, target_node: int, payload: bytes, cover: bool):
        now = datetime.now(timezone.utc)
        fragment = Fragment(surb_id, surb_key_tuple, target_node, payload, now, False, cover)
        self.cache[surb_id] = fragment
        self.out_counter += 1
        if surb_id in self.cache and not self.cache[surb_id].cover:
            metrics().increment(MetricField.UNACKED_MSG)

    @log_exceptions
    def received_surb(self, surb_id):
        self.set_acked(surb_id)
        entry = self.cache.get(surb_id)
        if entry is None:
            return None
        now = datetime.now(timezone.utc)
        start = entry.timestamp
        rtt = (now - start).total_seconds()
        if ConfigStore.resend_time > rtt:
            self.rtts.append(rtt)
            metrics().set(MetricField.LAST_RTT, rtt)
        metrics().set(MetricField.AVG_RTT, np.mean(self.rtts))
        self.in_counter += 1
        return entry.surb_key_tuble

    @log_exceptions
    def delete_cache_for_node(self, target_node):
        to_delete = [surb_id for surb_id, fragment in self.cache.items() if fragment.target_node == target_node]
        for surb_id in to_delete:
            self.set_acked(surb_id)
            del self.cache[surb_id]
        return len(to_delete)

    @log_exceptions
    def clear_acked_cache(self):
        to_delete = [surb_id for surb_id, fragment in self.cache.items() if fragment.acked]
        for surb_id in to_delete:
            del self.cache[surb_id]
        logging.debug(f"Cleared {len(to_delete)} acked fragments from cache.")
        return len(to_delete)

    def set_acked(self, surb_id: bytes):
        if surb_id in self.cache:
            self.cache[surb_id].acked = True
        if surb_id in self.cache and not self.cache[surb_id].cover:
            metrics().decrement(MetricField.UNACKED_MSG)

    @log_exceptions
    def get_older_than(self, seconds: float) -> List[Fragment]:
        self.clear_acked_cache()

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        to_resend = [fragment for fragment in self.cache.values() if fragment.timestamp < cutoff and not fragment.acked and not fragment.cover]

        for fragment in to_resend:
            self.set_acked(fragment.surb_id)  # mark as acked to prevent resending

        # logging.info(f"{self.in_counter=}, {self.out_counter=}, {len(to_resend)=}, {len(self.cache)=}")
        return to_resend

    @log_exceptions
    async def cache_all_acked(self):
        unacked_fragments = sum(1 for fragment in self.cache.values() if not fragment.acked and not fragment.cover)
        logging.info(f"Waiting for {unacked_fragments} SURBs.")
        return not unacked_fragments
