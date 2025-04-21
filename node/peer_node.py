import asyncio
import threading
import socket
import random
import time
import pickle
import logging

from petlib.bn import Bn
from petlib.ec import EcGroup, EcPt

from sphinxmix.SphinxParams import SphinxParams
from sphinxmix.SphinxClient import (
    create_forward_message, PFdecode, Relay_flag, Dest_flag,
    receive_forward, Nenc, pki_entry, pack_message, unpack_message
)
from sphinxmix.SphinxNode import sphinx_process

from key_store import KeyStore
from tcp_server import AsyncTCPPeer

MAX_HOPS = 3


class PeerNode:
    def __init__(self, node_id, port, peers):
        self._node_id = node_id
        self._port = port
        self._peers = peers
        self._params = SphinxParams(
            header_len=192,   # header size in bytes
            body_len=1024,    # payload size in bytes
            k=16,             # each hops' address in bytes
            dest_len=16       # destination address in bytes
        )
        self._group = self._params.group
        self._key_store = KeyStore()
        self.server = AsyncTCPPeer(node_id, port, peers, self.handle_message, 1216)


    async def handle_message(self, data: bytes):
        try:
            param_dict = {(self._params.max_len, self._params.m): self._params}
            _, (header, delta) = unpack_message(param_dict, data)
            x = self._key_store.get_x(self._node_id)
            tag, info, (header, delta), mac_key = sphinx_process(self._params, x, header, delta)
            routing = PFdecode(self._params, info)

            if routing[0] == Relay_flag:
                _, next_id = routing
                msg = pack_message(self._params, (header, delta))
                await self.server.send(next_id, msg)
            elif routing[0] == Dest_flag:
                dest, msg = receive_forward(self._params, mac_key, delta)
                logging.info(f"[{self._node_id}] Received message for {dest.decode()}: {msg.decode()}")
        except Exception as e:
            logging.warning(f"[{self._node_id}] Error in message handler: {e}")

    async def send_random_message(self):
        available_nodes = [nid for nid in self._peers if nid != self._node_id]
        path = [self._node_id] + random.sample(available_nodes, min(MAX_HOPS, len(available_nodes)))
        nodes_routing = list(map(Nenc, path))
        keys_nodes = [self._key_store.get_y(node_id) for node_id in path]
        topic = b"peer-message"
        message = f"Hi from node {self._node_id}".encode()
        header, delta = create_forward_message(self._params, nodes_routing, keys_nodes, topic, message)
        first_hop = path[0]
        msg_bytes = pack_message(self._params, (header, delta))
        await self.server.send(first_hop, msg_bytes)
        logging.info(f"[{self._node_id}] Sent message via path {path}")

    async def start(self):
        asyncio.create_task(self.server.start())
        await asyncio.sleep(1)
        while True:
            await asyncio.sleep(random.randint(3, 6))
            await self.send_random_message()