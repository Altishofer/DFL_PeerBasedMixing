import math
import secrets
import asyncio
import logging

class Mixer:
    def __init__(self, params):
        self._params = params
        self._enabled = params["enabled"]

    # inverse transform sampling of exponential distribution
    def secure_exponential(q):
        u = int.from_bytes(secrets.token_bytes(7), "big") / 2**56
        return -math.log(1 - u) / (1/q)

    async def mix_relay(self, relay):
        if self._enabled: 
            delay = Mixer.secure_exponential(self._params["mu"])
            logging.debug(f"mix relay, delay: {delay}")
            await asyncio.sleep(delay)
        await relay