import math
import secrets
import asyncio
import logging
from utils.exception_decorator import log_exceptions
from metrics.node_metrics import metrics, MetricField

class Mixer:
    def __init__(self, enabled, mix_lambda, mix_mu):
        self._outbox = asyncio.Queue()
        self._cover_generator = None
        self._outbox_loop = None
        self._config = {
            "nr_cover_bytes" : 100,
            "enabled": enabled,
            "lambda": mix_lambda, 
            "mu": mix_mu
        }

    # inverse transform sampling of exponential distribution
    @staticmethod
    def secure_exponential(q):
        u = int.from_bytes(secrets.token_bytes(7), "big") / 2**56
        if q == 0:
            q = 0.0001
        return -math.log(1 - u) / (1/q)

    async def mix_relay(self, relay):
        delay = 0
        if self._config["enabled"]: 
            delay = Mixer.secure_exponential(self._config["mu"])
        await asyncio.sleep(delay)
        metrics().set(MetricField.MIX_DELAY, delay)
        await relay

    @log_exceptions
    async def __outbox_loop(self):
        while (True):
            interval = 0
            if self._config["enabled"]:
                interval = Mixer.secure_exponential(self._config["lambda"])
                logging.debug(f"Checking outbox in: {interval}s")
            await asyncio.sleep(interval)
            metrics().set(MetricField.OUT_INTERVAL, interval)
            if not self._outbox.empty():
                out_message = self._outbox.get_nowait()
                logging.debug(f"sending message {out_message}")
                await out_message
                logging.debug(f"Sent message from outbox")
                self.__udpdate_message_metric(sending_covers=False)
            elif self._outbox.empty() and self._config["enabled"]:
                if self._cover_generator != None:
                    await self._cover_generator(nr_bytes=self._config["nr_cover_bytes"])
                    logging.debug(f"Sent cover from outbox")
                    self.__udpdate_message_metric(sending_covers=True)
                else:
                    logging.warning("No cover generator specified in mixer")

    async def start(self):
        self._outbox_loop = asyncio.create_task(self.__outbox_loop())
        logging.info(f"Started mixer, enabled: {self._config['enabled']}, lambda: {self._config['lambda']}, mu: {self._config['mu']}")

    def add_outgoing_message(self, message):
        self._outbox.put_nowait(message)

    def set_cover_generator(self, callback):
        self._cover_generator = callback

    def __udpdate_message_metric(self, sending_covers):
        if (sending_covers):
            metrics().increment(MetricField.COVERS_SENT)
        else:
            metrics().increment(MetricField.FRAGMENTS_SENT)
        metrics().set(MetricField.SENDING_COVERS, 1 if sending_covers else 0)
        metrics().set(MetricField.SENDING_FRAGMENTS, 0 if sending_covers else 1)
