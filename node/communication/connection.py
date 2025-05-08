import asyncio
import logging
from contextlib import suppress

from retry import retry

class Connection:

    def __init__(self, host: str, port: int, reader, writer):
        self._peer_id = host
        self._host = host
        self._port = port
        self._reader = reader
        self._writer = writer

    @classmethod
    @retry(tries=5, delay=1)
    async def create(cls, host: str, port: int):
        reader, writer = await asyncio.open_connection(host, port)
        logging.info(f"Connected to peer {host}:{port}")
        return cls(host, port, reader, writer)

    @retry(delay=4, tries=5)
    async def send(self, message: bytes):
        try:
            self._writer.write(message)
            await self._writer.drain()
            logging.debug(f"Sent {len(message)} bytes to peer {self._peer_id} at {self._host}:{self._port}")
        except Exception as e:
            logging.warning(f"Failed to send to peer {self._peer_id} at {self._host}:{self._port}: {e}")

    async def close(self):
        self._writer.close()
        await self._writer.wait_closed()











