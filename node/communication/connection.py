import asyncio
import logging

from metrics.node_metrics import metrics, MetricField
from utils.exception_decorator import log_exceptions


class Connection:
    def __init__(self, host: str, port: int, reader, writer, peer_id: int):
        self._host = host
        self._port = port
        self._reader = reader
        self._writer = writer
        self._peer_id = peer_id
        if self._writer:
            self._is_active = True
            logging.info(f"Connected to peer {peer_id}")
        else:
            self._is_active = False
            logging.warning(f"Connection to peer {peer_id} failed")

    @classmethod
    async def create(cls, host: str, port: int, peer_id: int):
        for attempt in range(3):
            try:
                reader, writer = await asyncio.open_connection(host, port)
                return cls(host, port, reader, writer, peer_id)
            except (ConnectionRefusedError, TimeoutError) as e:
                await asyncio.sleep(2)
        return cls(host, port, None, None, peer_id)

    async def send(self, message: bytes):
        if not self.is_active:
            logging.debug(f"No connection to peer {self._peer_id}")
            return

        try:
            self._writer.write(message)
        except (asyncio.TimeoutError, ConnectionResetError, BrokenPipeError, OSError) as e:
            logging.error(f"Exception sending to peer {self._peer_id}. Marking as inactive.")
            await self.close()
            return

        metrics().increment(MetricField.TOTAL_MSG_SENT)
        metrics().increment(MetricField.TOTAL_MBYTES_SENT, len(message) / 1048576)

    @log_exceptions
    async def close(self):
        self._is_active = False
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except (ConnectionResetError, BrokenPipeError, OSError):
                pass
        self._writer = None
        self._reader = None
        logging.warning(f"Connection to peer {self._peer_id} closed.")

    @property
    def is_active(self):
        return not (
                    self._writer is None or self._writer.transport is None or self._writer.transport.is_closing()) and self._is_active
