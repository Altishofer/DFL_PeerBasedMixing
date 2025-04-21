import asyncio
import random
import logging

from sphinxmix.SphinxClient import (
    create_forward_message, PFdecode, Relay_flag, Dest_flag,
    receive_forward, Nenc, pack_message, unpack_message
)
from sphinxmix.SphinxParams import SphinxParams
from sphinxmix.SphinxNode import sphinx_process
from key_store import KeyStore

from tcp_server import AsyncTCPPeer

class SphinxTransport:
    def __init__(self, node_id, port, peers, max_hops=3):
        self._node_id = node_id
        self._port = port
        self._peers = peers
        self._max_hops = max_hops

        self._params = SphinxParams(
            header_len=192,
            body_len=1024,
            k=16,
            dest_len=16
        )
        self._packet_size = self._params.max_len + self._params.m
        logging.info(self._packet_size)
        self._key_store = KeyStore()

        self._peer = AsyncTCPPeer(
            node_id=node_id,
            port=port,
            peers=peers,
            packet_size=self._packet_size,
            message_handler=self.__handle_incoming
        )

        self._incoming_queue = asyncio.Queue()

    async def start(self):
        asyncio.create_task(self._peer.start())

    async def send(self, payload: bytes):
        path = self.__build_random_path()
        nodes_routing = list(map(Nenc, path))
        keys_nodes = [self._key_store.get_y(nid) for nid in path]
        topic = b"peer-message"

        header, delta = create_forward_message(self._params, nodes_routing, keys_nodes, topic, payload)
        msg_bytes = pack_message(self._params, (header, delta))

        first_hop = path[0]
        await self._peer.send(first_hop, msg_bytes)
        logging.info(f"[{self._node_id}] Sent message via path {path}")

    async def receive(self) -> bytes:
        return await self._incoming_queue.get()

    async def __handle_incoming(self, data: bytes):
        try:
            param_dict = {(self._params.max_len, self._params.m): self._params}
            _, (header, delta) = unpack_message(param_dict, data)
            x = self._key_store.get_x(self._node_id)
            tag, info, (header, delta), mac_key = sphinx_process(self._params, x, header, delta)
            routing = PFdecode(self._params, info)

            if routing[0] == Relay_flag:
                _, next_id = routing
                msg = pack_message(self._params, (header, delta))
                await self._peer.send(next_id, msg)
            elif routing[0] == Dest_flag:
                dest, msg = receive_forward(self._params, mac_key, delta)
                logging.info(f"[{self._node_id}] ✅ Received message of length {len(msg)} for {dest.decode()}")
                await self._incoming_queue.put(msg)
        except Exception as e:
            logging.warning(f"[{self._node_id}] ❌ Error in transport: {e}")

    def __build_random_path(self):
        available_nodes = [nid for nid in self._peers if nid != self._node_id]
        return random.sample(available_nodes, min(self._max_hops, len(available_nodes)))