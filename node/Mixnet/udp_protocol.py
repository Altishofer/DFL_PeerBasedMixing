
import asyncio
import logging

from typing_extensions import override

class UdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, handle_connection_wrapper, server_started, outer_server):
        # logging.debug("⚡️ UdpProtocol.__init__ called")
        self.handle_connection_wrapper = handle_connection_wrapper
        self.server_started = server_started
        self.outer_server = outer_server

    @override
    def connection_made(self, transport):
        # logging.debug("⚡️ UdpProtocol.connection_made called")
        self.server_started.set()

    @override
    def datagram_received(self, data, addr):
        # logging.debug(f"⚡️ UdpProtocol.datagram_received from {addr}")
        try:
            self.outer_server._in_queue.put_nowait((data, addr))
        except asyncio.QueueFull:
            logging.exception(f"⚡️ UdpProtocol.datagram_received Queue Full")
