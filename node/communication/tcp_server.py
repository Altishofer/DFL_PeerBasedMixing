import asyncio
import logging

from communication.connection import Connection
from utils.exception_decorator import log_exceptions
from metrics.node_metrics import metrics, MetricField


class TcpServer:
    def __init__(self, node_id:int, port:int, peers:dict, message_handler, packet_size):
        self.node_id = node_id
        self.port = port
        self.peers = peers
        self.message_handler = message_handler
        self.packet_size = packet_size
        self._server = None
        self._hb_task = None
        self.connections = {} # node_id : Connection

    @log_exceptions
    async def start(self):
        self._server = await asyncio.start_server(
            self._handle_connection,
            "0.0.0.0",
            self.port
        )
        self._log_header("TCP SERVER")
        logging.info(f"TCP server listening on port {self.port}")
        async with self._server:
            await self._server.serve_forever()

    @log_exceptions
    async def connect_peers(self):
        for peer_id, (host, port) in list(self.peers.items()):
            await self.add_peer(peer_id, host, port)

    def is_active(self, peer_id):
        return peer_id in self.peers and peer_id in self.connections

    async def send(self, peer_id, message: bytes):
        if not self.is_active(peer_id):
            logging.debug(f"Skipping message to inactive peer {peer_id}")
            return
        try:
            metrics().increment(MetricField.MSG_SENT)
            metrics().increment(MetricField.BYTES_SENT, len(message))
            connection = self.connections[peer_id]
            await connection.send(message)
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            logging.warning(f"Send failed to peer {peer_id}")
            await self.remove_peer(peer_id)

    @log_exceptions
    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        pid_byte = await reader.readexactly(1)
        peer_id = int.from_bytes(pid_byte, "big")

        await self.add_peer(peer_id, f"node_{peer_id}", self.port)

        try:
            while True:
                data = await reader.readexactly(self.packet_size)
                await self.message_handler(data)
        except asyncio.exceptions.IncompleteReadError:
            logging.warning("Raised Incomplete Read Error")
            await self.remove_peer(peer_id)

    def _log_header(self, title):
        l = 30 - len(title) // 2
        logging.info(f"\n\n{'=' * l} {title} {'=' * l}")

    async def add_peer(self, peer_id: int, host: str, port: int):
        if peer_id in self.connections:
            return
        if peer_id == self.node_id:
            return
        try:
            self.peers[peer_id] = (host, port)
            self.connections[peer_id] = await Connection.create(self.node_id, host, port, peer_id)
        except:
            await self.remove_peer(peer_id)

    async def remove_peer(self, peer_id: int):
        conn = self.connections.pop(peer_id, None)
        if conn:
            logging.warning(f"Removed {peer_id} from active peers")
            await conn.close()
        self.peers.pop(peer_id, None)
