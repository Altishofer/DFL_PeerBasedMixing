import math
import secrets
import asyncio
import logging
from utils.exception_decorator import log_exceptions
from metrics.node_metrics import metrics, MetricField

class Mixer:
    def __init__(self, params):
        self._params = params
        self._enabled = params["enabled"]
        self._outbox = asyncio.Queue()
        self._cover_generator = None
        self._outbox_loop = None
        self._config = {
            "nr_cover_bytes" : 100
        }

    # inverse transform sampling of exponential distribution
    @staticmethod
    def secure_exponential(q):
        u = int.from_bytes(secrets.token_bytes(7), "big") / 2**56
        return -math.log(1 - u) / (1/q)

    async def mix_relay(self, relay):
        if self._enabled: 
            delay = Mixer.secure_exponential(self._params["mu"])
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(0)
        await relay

    @log_exceptions
    async def __outbox_loop(self):
        while (True):
            if (self._enabled):
                interval = Mixer.secure_exponential(self._params["lambda"])
                logging.debug(f"Checking outbox in: {interval}s")
                await asyncio.sleep(interval)
            else:
                await asyncio.sleep(0)

            if not self._outbox.empty():
                out_message = self._outbox.get_nowait()
                await out_message
                logging.debug(f"Sent message from outbox")
                metrics().increment(MetricField.FRAGMENTS_SENT)
            elif self._outbox.empty() and self._enabled:
                if self._cover_generator != None:
                    await self._cover_generator(nr_bytes=self._config["nr_cover_bytes"])
                    logging.debug(f"Sent cover from outbox")
                else:
                    logging.warning("No cover generator specified in mixer")

    async def start(self):
        self._outbox_loop = asyncio.create_task(self.__outbox_loop())

    def add_outgoing_message(self, message):
        self._outbox.put_nowait(message)

    def set_cover_generator(self, callback):
        self._cover_generator = callback
