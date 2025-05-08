import asyncio
import logging
from contextlib import suppress
from node.metrics.node_metrics import Metrics

from retry import retry

from utils.exception_decorator import log_exceptions


class Connection:

    def __init__(self, host: str, port: int, reader, writer):
        self._host = host
        self._port = port
        self._reader = reader
        self._writer = writer

    @classmethod
    @retry(tries=5, delay=1)
    @log_exceptions
    async def create(cls, host: str, port: int):
        reader, writer = await asyncio.open_connection(host, port)
        logging.info(f"Connected to peer {host}:{port}")
        return cls(host, port, reader, writer)

    @retry(tries=5, delay=1)
    @log_exceptions
    async def send(self, message: bytes):
        self._writer.write(message)
        await self._writer.drain()
        logging.debug(f"Sent {len(message)} bytes to peer at {self._host}:{self._port}")

    @log_exceptions
    async def close(self):
        self._writer.close()
        await self._writer.wait_closed()

