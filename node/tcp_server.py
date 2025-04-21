import asyncio
import logging
from contextlib import suppress

from retry import retry


class TCP_Server:
    def __init__(self, node_id, port, peers, message_handler, packet_size):
        self.node_id = node_id
        self.port = port
        self.peers = peers  # peer_id: (host, port)
        self.message_handler = message_handler
        self.packet_size = packet_size
        self._server = None

    async def start(self):
        self._server = await asyncio.start_server(
            self._handle_connection,
            "0.0.0.0",
            self.port
        )
        logging.info(f"TCP server listening on port {self.port}")
        async with self._server:
            await self._server.serve_forever()

    @retry(delay=4, tries=5)
    async def send(self, peer_id, message: bytes):
        host, port = self.peers[peer_id]
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.write(message)
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            logging.debug(f"Sent {len(message)} bytes to peer {peer_id} at {host}:{port}")
        except Exception as e:
            logging.warning(f"Failed to send to peer {peer_id} at {host}:{port}: {e}")

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer_info = writer.get_extra_info("peername")
        try:
            data = await reader.read(65536)
            logging.debug(f"Received {len(data)} bytes from {peer_info}")
            await self.message_handler(data)
        except asyncio.IncompleteReadError:
            logging.warning(f"Incomplete message from {peer_info}")
        except Exception as e:
            logging.warning(f"Error handling data from {peer_info}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logging.debug(f"Closed connection from {peer_info}")