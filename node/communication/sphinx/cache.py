import hashlib
import json
import sys
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
    payload: dict
    timestamp: datetime


class Cache:

    def __init__(self):
        self.cache = {}

    @log_exceptions
    def new_fragment(self, surb_id:bytes, surb_key_tuple:tuple, target_node:int, payload:dict):
        metrics().increment(MetricField.FRAGMENT_RECEIVED)
        now = datetime.now(timezone.utc)
        fragment = Fragment(surb_id, surb_key_tuple, target_node, payload, now)
        self.cache[surb_id] = fragment

    @log_exceptions
    def received_surb(self, surb_id):
        metrics().increment(MetricField.SURB_RECEIVED)
        fragment = self.cache.get(surb_id)
        del self.cache[surb_id]
        return fragment.surb_key_tuble

    @log_exceptions
    def get_older_than(self, seconds: float) -> List[Fragment]:
        metrics().increment(MetricField.SURB_RECEIVED)
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        to_resend = [fragment for fragment in self.cache.values() if fragment.timestamp < cutoff]
        metrics().increment(MetricField.FRAGMENT_RESENT, len(to_resend))
        return to_resend
