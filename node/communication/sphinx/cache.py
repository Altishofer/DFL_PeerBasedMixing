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
    digest: int


class Cache:

    def __init__(self):
        self.cache = {}
        self.digests = {}

    @log_exceptions
    def new_fragment(self, surb_id:bytes, surb_key_tuple:tuple, target_node:int, payload:dict):
        now = datetime.now(timezone.utc)
        digest = hash(payload)
        fragment = Fragment(surb_id, surb_key_tuple, target_node, payload, now, digest)
        if digest in self.digests:
            prev_surb_id = self.digests[digest]
            del self.cache[prev_surb_id]
        self.digests[digest] = surb_id
        self.cache[surb_id] = fragment

    @log_exceptions
    def _compute_digest(self, payload: dict) -> str:
        serialized = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(serialized).hexdigest()

    @log_exceptions
    def received_surb(self, surb_id):
        fragment = self.cache.get(surb_id)

        if not fragment:
            logging.warning(f"[Cache] SURB ID not found: {surb_id.hex()}")
            logging.warning(f"[Cache] Available keys: {[k.hex() for k in self.cache.keys()]}")
            return None

        # del self.cache[surb_id]
        return fragment.surb_key_tuble

    @log_exceptions
    def get_older_than(self, seconds: float) -> List[Fragment]:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        return [fragment for fragment in self.cache.values() if fragment.timestamp < cutoff]
