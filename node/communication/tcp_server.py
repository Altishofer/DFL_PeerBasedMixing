import asyncio
import logging
import traceback

from communication.connection import Connection
from utils.exception_decorator import log_exceptions
from metrics.node_metrics import metrics, MetricField
from utils.logging_config import log_header


class TcpServer:
    def __init__(self, node_id: int, port: int, peers: dict, message_handler, packet_size):
        self.node_id = node_id
        self.port = port
        self.peers = peers
        self.message_handler = message_handler
        self.packet_size = packet_size
        self._server = None
        self.connections = {}
        # asyncio.create_task(self._reconnect_loop())

    @log_exceptions
    async def start(self):
        log_header("TCP server")
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
        for pid in self.peers.keys():
            await self.add_peer(pid)

    def is_active(self, peer_id):
        return self.connections.get(peer_id).is_active

    def active_peers(self):
        active_peers = [peer_id for peer_id in self.connections if self.is_active(peer_id)]
        metrics().set(MetricField.ACTIVE_PEERS, len(active_peers))
        return active_peers

    async def send_to_peer(self, peer_id, message: bytes):
        if not self.is_active(peer_id):
            logging.debug(f"Cannot send message to peer {peer_id}: not connected or inactive.")
            return
        try:
            await asyncio.wait_for(self.connections[peer_id].send(message), timeout=1.0)
        except (ConnectionResetError, BrokenPipeError, OSError, asyncio.TimeoutError) as e:
            await self.connections[peer_id].close()
            logging.warning(f"Send failed to peer {peer_id}: {e}")

    @log_exceptions
    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peername = writer.get_extra_info("peername")
        try:
            while True:
                data = await reader.readexactly(self.packet_size)
                await self.message_handler(data, peername)
        except asyncio.exceptions.IncompleteReadError:
            logging.error(f"Incomplete read error for node {peername}.")
            peer_id = int(peername[0].split('.')[-1]) - 1
            await self.remove_peer(peer_id)

    def is_me(self, peer_id: int):
        return peer_id == self.node_id

    async def add_peer(self, peer_id: int):

        if (peer_id in self.connections and self.is_active(peer_id)) or self.is_me(peer_id):
            return

        host, port = self.peers[peer_id]
        self.connections[peer_id] = await Connection.create(host, port, peer_id)

    async def remove_peer(self, peer_id: int):
        if peer_id not in self.connections: return
        await self.connections[peer_id].close()

    async def _reconnect_loop(self):
        while True:
            for pid in self.peers.keys():
                await self.add_peer(pid)
            await asyncio.sleep(5)

    async def close_all_connections(self):
        for peer_id in list(self.connections.keys()):
            await self.connections[peer_id].close()
        logging.warning("All connections closed.")
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            logging.warning("TCP server stopped.")
