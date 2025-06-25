import math
import secrets
import asyncio
from asyncio import QueueEmpty
import logging

class Mixer:
    def __init__(self, params):
        self._params = params
        self._enabled = params["enabled"]
        self._outbox = asyncio.Queue()
        self._cover_generator = None
        self._outbox_loop = None

    # inverse transform sampling of exponential distribution
    @staticmethod
    def secure_exponential(q):
        u = int.from_bytes(secrets.token_bytes(7), "big") / 2**56
        return -math.log(1 - u) / (1/q)

    async def mix_relay(self, relay):
        if self._enabled: 
            delay = Mixer.secure_exponential(self._params["mu"])
            await asyncio.sleep(delay)
        await relay

    async def __outbox_loop(self):
        while (True):
            interval = Mixer.secure_exponential(self._params["lambda"])
            logging.debug(f"Checking outbox in: {interval}s")
            await asyncio.sleep(interval)
            if not self._outbox.empty():
                logging.debug(f"Sending message from outbox")
                out_message = self._outbox.get_nowait()
                await out_message
            else:
                if self._cover_generator != None:
                    logging.debug(f"Sending cover from outbox")
                    await self._cover_generator()
                else:
                    logging.warning("No cover generator specified in mixer")

    async def start(self):
        self._outbox_loop = asyncio.create_task(self.__outbox_loop())

    def add_outgoing_message(self, message):
        self._outbox.put_nowait(message)

    def set_cover_generator(self, callback):
        self._cover_generator = callback
