import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List
import logging

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
        now = datetime.now(timezone.utc)
        fragment = Fragment(surb_id, surb_key_tuple, target_node, payload, now)
        self.cache[surb_id] = fragment

    @log_exceptions
    def received_surb(self, surb_id):
        fragment = self.cache.get(surb_id)
        del self.cache[surb_id]
        return fragment.surb_key_tuble

    @log_exceptions
    def get_older_than(self, seconds: float) -> List[Fragment]:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        return [fragment for fragment in self.cache.values() if fragment.timestamp < cutoff]
