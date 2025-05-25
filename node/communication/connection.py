import asyncio
import logging

from retry import retry

from utils.exception_decorator import log_exceptions


class Connection:

    def __init__(self, host: str, port: int, reader, writer, peer_id):
        self._host = host
        self._port = port
        self._reader = reader
        self._writer = writer
        self._peer_id = peer_id

    @classmethod
    async def create(cls, my_peer_id: int, host: str, port: int, peer_id: int):
        reader, writer = await asyncio.open_connection(host, port)
        writer.write(my_peer_id.to_bytes(1, "big"))
        await writer.drain()
        logging.info(f"Connected to peer {host}:{port}")
        return cls(host, port, reader, writer, peer_id)

    async def send(self, message: bytes):
        self._writer.write(message)
        await self._writer.drain()
        logging.debug(f"Sent {len(message)} bytes to peer at {self._host}:{self._port}")

    @log_exceptions
    async def close(self):
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except ConnectionResetError:
            logging.warning(f"Peer {self._peer_id} already reset connection.")


