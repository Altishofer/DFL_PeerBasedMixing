import asyncio
import random
import logging
import struct
import sys
import time

import msgpack

from sphinxmix.SphinxClient import (
    create_forward_message, PFdecode, Relay_flag, Dest_flag, Surb_flag,
    receive_forward, Nenc, pack_message, unpack_message,
    create_surb, package_surb, receive_surb
)
from sphinxmix.SphinxParams import SphinxParams
from sphinxmix.SphinxNode import sphinx_process

from communication.sphinx_router import SphinxRouter
from node.communication.key_store import KeyStore
from node.communication.tcp_server import TcpServer
from utils.exception_decorator import log_exceptions


class SphinxTransport:
    def __init__(self, node_id, port, peers):
        self._node_id = node_id
        self._port = port
        self._peers = peers

        self._params = SphinxParams(
            header_len=192,
            body_len=1024,
            k=16,
            dest_len=16
        )
        self._packet_size = 1253

        self.sphinx_router = SphinxRouter(
            node_id,
            peers,
            self._params,
        )

        self._peer = TcpServer(
            node_id=node_id,
            port=port,
            peers=peers,
            packet_size=self._packet_size,
            message_handler=self.__handle_incoming
        )

        self._incoming_queue = asyncio.Queue()

    @log_exceptions
    async def start(self):
        asyncio.create_task(self._peer.start())
        await asyncio.sleep(5)
        await self._peer.connect_peers()
        await asyncio.sleep(5)

    @log_exceptions
    async def send(self, payload: bytes, target_node: int = None):
        path, msg_bytes = self.sphinx_router.create_forward_msg(target_node, payload)
        await self._peer.send(path[0], msg_bytes)

    @log_exceptions
    async def receive(self) -> bytes:
        return await self._incoming_queue.get()

    @log_exceptions
    async def __unpack_payload_and_send_surb(self, payload_bytes: bytes):
        try:
            nymtuple, payload = payload_bytes
            await self._incoming_queue.put(payload)
            msg_bytes, first_hop = self.sphinx_router.create_surb_reply(nymtuple)
            await self._peer.send(first_hop, msg_bytes)
            logging.debug("Sent SURB-based reply.")
        except Exception:
            logging.error(f"Error __unpack_payload_and_send_surb", exc_info=True)

    @log_exceptions
    async def __handle_incoming(self, data: bytes):
        try:
            unpacked = self.sphinx_router.process_incoming(data)
            await self.__handle_routing_decision(*unpacked)
        except Exception as e:
            logging.error(f"Error handling_incoming", exc_info=True)

    @log_exceptions
    async def __handle_routing_decision(self, routing, header, delta, mac_key):
        if routing[0] == Relay_flag:
            await self._peer.send(routing[1], pack_message(self._params, (header, delta)))
        elif routing[0] == Dest_flag:
            dest, msg = receive_forward(self._params, mac_key, delta)
            await self.__unpack_payload_and_send_surb(msg)
        elif routing[0] == Surb_flag:
            self.sphinx_router.decrypt_surb(delta, routing[2])
