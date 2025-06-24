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
        return -math.log(1 - u) / q

    async def mix_relay(self, send):
        logging.debug(f"mix relay, params: {self._params}")
        if not self._enabled:
            send()
            return
        duration = self.secure_exponential(self._params["mu"])
        asyncio.sleep(duration)
        send()