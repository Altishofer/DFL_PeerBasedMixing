import math
import secrets
import asyncio
import logging
from utils.exception_decorator import log_exceptions
from metrics.node_metrics import metrics, MetricField
from dataclasses import dataclass
from typing import Awaitable, Callable

@dataclass
class QueueObject:
    send_message: Awaitable
    update_metrics: Callable

class Mixer:
    def __init__(self, enabled, mix_lambda, shuffle):
        self._outbox = []
        self._cover_generator = None
        self._outbox_loop = None
        self._config = {
            "enabled": enabled,
            "lambda": mix_lambda, 
            "shuffle": shuffle,
            "nr_cover_bytes": 100,
        }

    # inverse transform sampling of exponential distribution
    @staticmethod
    def secure_exponential(q):
        u = int.from_bytes(secrets.token_bytes(7), "big") / 2**56
        if q == 0:
            q = 0.0001
        return -math.log(1 - u) / (1/q)
    
    @log_exceptions
    async def __outbox_loop(self):
        while (True):
            interval = 0
            if self._config["enabled"]:
                interval = Mixer.secure_exponential(self._config["lambda"])
            await asyncio.sleep(interval)
            metrics().set(MetricField.OUT_INTERVAL, interval)
            if not self.queue_is_empty():
                queue_obj = self._outbox.pop()
                await queue_obj.send_message()
                queue_obj.update_metrics()
                self.__udpdate_message_metric(sending_covers=False)
            elif self.queue_is_empty() and self._config["enabled"]:
                if self._cover_generator != None:
                    await self._cover_generator(nr_bytes=self._config["nr_cover_bytes"])
                    self.__udpdate_message_metric(sending_covers=True)
                else:
                    logging.warning("No cover generator specified in mixer")

    async def start(self, cover_generator: Callable):
        self._outbox_loop = asyncio.create_task(self.__outbox_loop())
        self._cover_generator = cover_generator
        logging.info(f"Started mixer, enabled: {self._config['enabled']}, lambda: {self._config['lambda']}, shuffle: {self._config['shuffle']}")

    def push_to_outbox(self, msg_coroutine : Awaitable, update_metrics: Callable):
        queue_obj = QueueObject(msg_coroutine, update_metrics)
        
        idx = 0
        if self._config["shuffle"] and not self.queue_is_empty():
            idx = secrets.randbelow(len(self._outbox) + 1)

        logging.debug(f"inserted into queue of length: {len(self._outbox)}, at index: {idx}")
        self._outbox.insert(idx, queue_obj)

    def queue_is_empty(self):
        return len(self._outbox) == 0

    def __udpdate_message_metric(self, sending_covers):
        if (sending_covers):
            metrics().increment(MetricField.COVERS_SENT)
        metrics().set(MetricField.SENDING_COVERS, 1 if sending_covers else 0)
        metrics().set(MetricField.SENDING_MESSAGES, 0 if sending_covers else 1)
