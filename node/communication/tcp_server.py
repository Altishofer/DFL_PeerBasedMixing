import asyncio
import logging
from contextlib import suppress

from retry import retry

from communication.connection import Connection


class TcpServer:
    def __init__(self, node_id:str, port:int, peers:dict, message_handler, packet_size):
        self.node_id = node_id
        self.port = port
        self.peers = peers
        self.message_handler = message_handler
        self.packet_size = packet_size
        self._server = None
        self.connections = {} # node_id : Connection

    async def start(self):
        self._server = await asyncio.start_server(
            self._handle_connection,
            "0.0.0.0",
            self.port
        )
        logging.info(f"TCP server listening on port {self.port}")
        async with self._server:
            await self._server.serve_forever()

    async def connect_peers(self):
        self.connections = {
        peer_id: await Connection.create(host, port)
        for peer_id, (host, port) in
        self.peers.items() if peer_id != self.node_id
        }

    async def send(self, peer_id, message: bytes):
        connection = self.connections[peer_id]
        await connection.send(message)

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer_info = writer.get_extra_info("peername")
        try:
            while True:
                data = await reader.readexactly(self.packet_size)
                await self.message_handler(data)
        except Exception as e:
            logging.warning(f"Error handling data from {peer_info}: {e}")