import asyncio
import logging
import math
import secrets
from dataclasses import dataclass
from typing import Awaitable, Callable
from scipy.stats import truncnorm

from metrics.node_metrics import metrics, MetricField
from utils.config_store import ConfigStore
from utils.exception_decorator import log_exceptions
from utils.logging_config import log_header

from metrics.node_metrics import metrics, MetricField
from utils.config_store import ConfigStore
from utils.exception_decorator import log_exceptions
from utils.logging_config import log_header


@dataclass
class QueueObject:
    send_message: Awaitable
    update_metrics: Callable

class Mixer:
    def __init__(self, cover_generator):
        self._outbox = []
        self._queue = []
        self._cover_generator = cover_generator
        self._outbox_loop = None
        self._next_send = None
        self._running = False

    # inverse transform sampling of exponential distribution
    @staticmethod
    def secure_exponential(q):
        u = int.from_bytes(secrets.token_bytes(7), "big") / 2 ** 56
        if q == 0:
            return 0.001
        sleep_time = -math.log(1 - u) / (1 / q)
        # logging.warning(f"Secure exponential sleep time: {sleep_time} seconds, max_rate = {1 / sleep_time}")
        return min(sleep_time, 0.001)

    @staticmethod
    def secure_uniform(mu=0, sigma=1):
        u1 = (secrets.randbits(53) + 1) / (2 ** 53)  # avoid 0
        u2 = (secrets.randbits(53) + 1) / (2 ** 53)

        # Box-Muller transform
        z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2 * math.pi * u2)
        return mu + sigma * z0

    @staticmethod
    def secure_lognormal(mean, std):
        sigma_log = math.sqrt(math.log(1 + (std ** 2 / mean ** 2)))
        mu_log = math.log(mean) - 0.5 * sigma_log ** 2

        # Secure normal sample via Box-Muller
        u1 = (secrets.randbits(53) + 1) / (2 ** 53)
        u2 = (secrets.randbits(53) + 1) / (2 ** 53)
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
        self._next_send = asyncio.get_event_loop().time()
        try:
            while self._running:
                self.__update_outbox()

                queue_obj = self._outbox.pop()
                await queue_obj.send_message()
                queue_obj.update_metrics()

                now = asyncio.get_event_loop().time()
                interval = Mixer.secure_truncated_normal(ConfigStore.mix_mu, ConfigStore.mix_std)
                self._next_send += interval
                sleep_time = max(0, self._next_send - now)
                metrics().set(MetricField.OUT_INTERVAL, sleep_time)
                await asyncio.sleep(sleep_time)
        except Exception:
            logging.exception("Exception in __outbox_loop")
        finally:
            logging.info("Outbox loop exited")

    async def start(self):
        if ConfigStore.mix_enabled:
            self._running = True
            self._outbox_loop = asyncio.create_task(self.__outbox_loop())
            log_header("Peer-Based Mixer")
            logging.info(f"Enabled: {ConfigStore.mix_enabled}")
            logging.info(f"Shuffle: {ConfigStore.mix_shuffle}")
            logging.info(f"N Cover Bytes: {ConfigStore.nr_cover_bytes}")
        else:
            logging.info(f"Mixer disabled")

    async def stop(self):
        self._running = False
        try:
            await self._outbox_loop
        except asyncio.CancelledError:
            logging.warning("Outbox loop was forcibly cancelled.")

    def __update_outbox(self):
        if not self.outbox_is_empty():
            return

        for _ in range(ConfigStore.mix_outbox_size):
            if not self.queue_is_empty():
                self._outbox.append(self._queue.pop(0))
            else:
                self._outbox.append(self.__create_cover_item())

        if ConfigStore.mix_shuffle:
            self.__shuffle_outbox()

    def __shuffle_outbox(self):
        n = len(self._outbox)
        for i in range(n):
            j = i + secrets.randbelow(n - i)
            tmp = self._outbox[j]
            self._outbox[j] = self._outbox[i]
            self._outbox[i] = tmp

    def __create_cover_item(self):
        queue_obj = QueueObject(
            send_message=self.__create_cover_task,
            update_metrics=lambda: self.__update_message_metric(True),
        )
        return queue_obj

    async def queue_item(self, msg_coroutine: Awaitable, update_metrics: Callable):
        queue_obj = QueueObject(
            send_message=msg_coroutine,
            update_metrics=lambda: (
                update_metrics(),
                self.__update_message_metric(False),
            )
        )

        if ConfigStore.mix_enabled:
            self._queue.append(queue_obj)
            metrics().set(MetricField.QUEUED_PACKAGES, len(self._queue))
        else:
            start = asyncio.get_event_loop().time()
            await queue_obj.send_message()
            queue_obj.update_metrics()
            metrics().set(MetricField.SENDING_TIME, asyncio.get_event_loop().time() - start)

    def outbox_is_empty(self):
        return len(self._outbox) == 0

    def queue_is_empty(self):
        return len(self._queue) == 0

    def __update_message_metric(self, sending_covers):
        if sending_covers:
            metrics().increment(MetricField.COVERS_SENT)
        metrics().set(MetricField.SENDING_COVERS, 1 if sending_covers else 0)
        metrics().set(MetricField.SENDING_MESSAGES, 0 if sending_covers else 1)

    async def __create_cover_task(self):
        cover = await self._cover_generator()
        await cover()
