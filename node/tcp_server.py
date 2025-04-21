import asyncio
import logging

class AsyncTCPServer:
    def __init__(self, node_id, port, message_handler):
        self.node_id = node_id
        self.port = port
        self.message_handler = message_handler
        self._server = None

    async def start(self):
        self._server = await asyncio.start_server(self._handle_connection, "0.0.0.0", self.port)
        logging.info(f"[{self.node_id}] TCP server listening on port {self.port}")
        async with self._server:
            await self._server.serve_forever()

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer_info = writer.get_extra_info("peername")
        logging.info(f"[{self.node_id}] Incoming connection from {peer_info}")
        try:
            while not reader.at_eof():
                data = await reader.read(65536)
                if not data:
                    logging.info(f"[{self.node_id}] Empty data from {peer_info}, closing connection.")
                    break
                logging.debug(f"[{self.node_id}] Received {len(data)} bytes from {peer_info}")
                await self.message_handler(data)
        except Exception as e:
            logging.warning(f"[{self.node_id}] Error handling data from {peer_info}: {e}")
        finally:
            logging.info(f"[{self.node_id}] Closing connection from {peer_info}")
            writer.close()
            await writer.wait_closed()


class AsyncConnectionPool:
    def __init__(self, peers):
        self.peers = peers  # peer_id: (host, port)
        self.connections = {}  # peer_id: StreamWriter

    async def get_writer(self, peer_id):
        writer = self.connections.get(peer_id)
        if writer is None or writer.is_closing():
            host, port = self.peers[peer_id]
            try:
                logging.debug(f"Attempting connection to peer {peer_id} at {host}:{port}")
                reader, writer = await asyncio.open_connection(host, port)
                self.connections[peer_id] = writer
                logging.info(f"Connected to peer {peer_id} at {host}:{port}")
            except Exception as e:
                logging.warning(f"Failed to connect to peer {peer_id} at {host}:{port}: {e}")
                raise
        return writer

    async def send(self, peer_id, message: bytes):
        try:
            writer = await self.get_writer(peer_id)
            writer.write(message)
            await writer.drain()
            logging.debug(f"Sent {len(message)} bytes to peer {peer_id}")
        except Exception as e:
            logging.warning(f"Send to peer {peer_id} failed: {e}")
            self.close_connection(peer_id)

    def close_connection(self, peer_id):
        writer = self.connections.pop(peer_id, None)
        if writer and not writer.is_closing():
            logging.info(f"Closing connection to peer {peer_id}")
            writer.close()
        else:
            logging.debug(f"No active connection to close for peer {peer_id}")

    async def close_all(self):
        logging.info("Closing all peer connections")
        for peer_id in list(self.connections.keys()):
            self.close_connection(peer_id)
        await asyncio.sleep(0.1)