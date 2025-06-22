import asyncio
import logging
import traceback

from communication.connection import Connection
from utils.exception_decorator import log_exceptions
from metrics.node_metrics import metrics, MetricField


class TcpServer:
    def __init__(self, node_id: int, port: int, peers: dict, message_handler, packet_size):
        self.node_id = node_id
        self.port = port
        self.peers = peers
        self._peer_cfg = peers.copy()
        self.message_handler = message_handler
        self.packet_size = packet_size
        self._server = None
        self.connections = {}
        asyncio.create_task(self._reconnect_loop())

    @log_exceptions
    async def start(self):
        self._server = await asyncio.start_server(
            self._handle_connection,
            "0.0.0.0",
            self.port
        )
        logging.info(f"TCP server listening on port {self.port}")
        async with self._server:
            await self._server.serve_forever()

    @log_exceptions
    async def connect_peers(self):
        for pid in list(self._peer_cfg.keys()):
            await self.add_peer(pid)

    def is_active(self, peer_id):
        return peer_id in self.connections

    def active_peers(self):
        return [peer_id for peer_id in self.connections]

    async def send(self, peer_id, message: bytes):
        try:
            metrics().increment(MetricField.MSG_SENT)
            metrics().increment(MetricField.BYTES_SENT, len(message))
            await asyncio.wait_for(self.connections[peer_id].send(message), timeout=10.0)
        except (ConnectionResetError, BrokenPipeError, OSError, asyncio.TimeoutError) as e:
            logging.warning(f"Send failed to peer {peer_id}: {e}")
            logging.warning(f"Exception details: {traceback.format_exc()}")

    @log_exceptions
    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            while True:
                data = await reader.readexactly(self.packet_size)
                await self.message_handler(data)
        except asyncio.exceptions.IncompleteReadError:
            logging.error(f"INCOMPLETE READ ERROR")

    async def add_peer(self, peer_id: int):
        if peer_id in self.connections or peer_id == self.node_id or peer_id not in self._peer_cfg:
            return
        host, port = self._peer_cfg[peer_id]
        try:
            self.connections[peer_id] = await Connection.create(host, port, peer_id)
            self.peers[peer_id] = (host, port)
        except Exception as e:
            logging.debug(f"Failed to connect to peer {peer_id}: {e}")

    async def remove_peer(self, peer_id: int):
        conn = self.connections.pop(peer_id, None)
        if conn:
            await conn.close()
        self.peers.pop(peer_id, None)

    async def _reconnect_loop(self):
        while True:
            for pid in list(self._peer_cfg.keys()):
                await self.add_peer(pid)
            await asyncio.sleep(5)
