import math
import secrets
import asyncio
import logging
import time

from utils.logging_config import log_header
from utils.config_store import ConfigStore
from utils.exception_decorator import log_exceptions
from metrics.node_metrics import metrics, MetricField
from dataclasses import dataclass
from typing import Awaitable, Callable
from scipy.stats import truncnorm

from metrics.node_metrics import metrics, MetricField
from utils.config_store import ConfigStore
from utils.exception_decorator import log_exceptions
from utils.logging_config import log_header


@dataclass
class QueueObject:
    send_message: Awaitable
    update_metrics: Callable

class Mixer:
    def __init__(self):
        self._outbox = []
        self._queue = []
        self._cover_generator = None
        self._outbox_loop = None

    # inverse transform sampling of exponential distribution
    @staticmethod
    def secure_exponential(q):
        u = int.from_bytes(secrets.token_bytes(7), "big") / 2**56
        if q == 0:
            return 0.001
        sleep_time = -math.log(1 - u) / (1/q)
        # logging.warning(f"Secure exponential sleep time: {sleep_time} seconds, max_rate = {1 / sleep_time}")
        return min(sleep_time, 0.001)
    
    @staticmethod
    def secure_uniform(mu=0, sigma=1):
        u1 = (secrets.randbits(53) + 1) / (2**53)  # avoid 0
        u2 = (secrets.randbits(53) + 1) / (2**53)

        # Box-Muller transform
        z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2 * math.pi * u2)
        return mu + sigma * z0
    
    @staticmethod
    def secure_lognormal(mean, std):
        sigma_log = math.sqrt(math.log(1 + (std**2 / mean**2)))
        mu_log = math.log(mean) - 0.5 * sigma_log**2

        # Secure normal sample via Box-Muller
        u1 = (secrets.randbits(53) + 1) / (2**53)
        u2 = (secrets.randbits(53) + 1) / (2**53)
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2 * math.pi * u2)

        return math.exp(mu_log + sigma_log * z)
    
    @staticmethod
    def secure_truncated_normal(mu=0.005, sigma=0.002, a=0.0, b=0.1):
        # Generate secure uniform random number in [0,1)
        u = secrets.SystemRandom().random()
        
        lower, upper = (a - mu) / sigma, (b - mu) / sigma
        
        return truncnorm.ppf(u, lower, upper, loc=mu, scale=sigma)

    @log_exceptions
    async def __outbox_loop(self):
        while True:
            if ConfigStore.mix_enabled:
                self.__update_outbox()

                interval = Mixer.secure_truncated_normal(ConfigStore.mix_mu, ConfigStore.mix_std, 0, 0.1)
                metrics().set(MetricField.OUT_INTERVAL, interval)
                start = asyncio.get_event_loop().time()

                queue_obj = self._outbox.pop()
                await queue_obj.send_message()
                queue_obj.update_metrics()

                elapsed = asyncio.get_event_loop().time() - start
                await asyncio.sleep(max(0, interval - elapsed))
            elif not self.queue_is_empty():
                queue_obj = self._queue.pop(0)

                await asyncio.sleep(0.01)

    async def start(self, cover_generator: Callable):
        if (ConfigStore.mix_enabled):
            self._outbox_loop = asyncio.create_task(self.__outbox_loop())
            self._cover_generator = cover_generator
            log_header("Peer-Based Mixer")
            logging.info(f"Enabled: {ConfigStore.mix_enabled}")
            logging.info(f"Shuffle: {ConfigStore.mix_shuffle}")
            logging.info(f"N Cover Bytes: {ConfigStore.nr_cover_bytes}")
        else:
            logging.info(f"Mixer disabled")

    def __update_outbox(self): 
        if (not self.outbox_is_empty()):
            return

        for _ in range(ConfigStore.mix_outbox_size):
            if (not self.queue_is_empty()):
                self._outbox.append(self._queue.pop(0))
            else:
                self._outbox.append(self.__create_cover_item())

        if (ConfigStore.mix_shuffle):
            self.__shuffle_outbox()

    def __shuffle_outbox(self):
        n = len(self._outbox)
        for i in range(n):
            j = i + secrets.randbelow(n-i)
            tmp = self._outbox[j]
            self._outbox[j] = self._outbox[i]
            self._outbox[i] = tmp
        

    def __create_cover_item(self):
        cover = QueueObject(
            send_message=self._cover_generator,
            update_metrics=lambda: self.__update_message_metric(True),
        )
        return cover

    async def queue_item(self, msg_coroutine : Awaitable, update_metrics: Callable):
        queue_obj = QueueObject(
            send_message=msg_coroutine,
            update_metrics=lambda: (
                update_metrics(),
                self.__update_message_metric(False)
            )
        )

        if (ConfigStore.mix_enabled):
            self._queue.append(queue_obj)
            metrics().set(MetricField.QUEUED_PACKAGES, len(self._outbox))
        else:
            await queue_obj.send_message()
            queue_obj.update_metrics()

    def outbox_is_empty(self):
        return len(self._outbox) == 0
    
    def queue_is_empty(self):
        return len(self._queue) == 0
    
    def __update_message_metric(self, sending_covers):
        if sending_covers:
            metrics().increment(MetricField.COVERS_SENT)
        metrics().set(MetricField.SENDING_COVERS, 1 if sending_covers else 0)
        metrics().set(MetricField.SENDING_MESSAGES, 0 if sending_covers else 1)

