import asyncio
import logging

from retry import retry

from utils.exception_decorator import log_exceptions


class Connection:
    def __init__(self, host: str, port: int, reader, writer, peer_id: int):
        self._host = host
        self._port = port
        self._reader = reader
        self._writer = writer
        self._peer_id = peer_id
        logging.info(f"Connected to peer {host}:{port} with id {peer_id}")

    @classmethod
    async def create(cls, host: str, port: int, peer_id: int):
        reader, writer = await asyncio.open_connection(host, port)
        return cls(host, port, reader, writer, peer_id)

    @retry(tries=3, delay=2)
    async def send(self, message: bytes):
        self._writer.write(message)
        await self._writer.drain()

    @log_exceptions
    async def close(self):
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
