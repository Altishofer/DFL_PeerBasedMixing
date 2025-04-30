import asyncio
import random
import logging
import struct
import msgpack

from sphinxmix.SphinxClient import (
    create_forward_message, PFdecode, Relay_flag, Dest_flag, Surb_flag,
    receive_forward, Nenc, pack_message, unpack_message,
    create_surb, package_surb, receive_surb
)
from sphinxmix.SphinxParams import SphinxParams
from sphinxmix.SphinxNode import sphinx_process

from node.communication.key_store import KeyStore
from node.communication.tcp_server import TcpServer

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
        self._key_store = KeyStore()

        self._peer = TcpServer(
            node_id=node_id,
            port=port,
            peers=peers,
            packet_size=self._packet_size,
            message_handler=self.__handle_incoming
        )

        self._incoming_queue = asyncio.Queue()
        self._surb_key_store = {}

    async def start(self):
        asyncio.create_task(self._peer.start())

    async def send(self, payload: bytes, target_node: int = None):
        path, nodes_routing, keys_nodes = self.__build_forward_path(target_node)
        backward_path, nodes_routing_back, keys_nodes_back = self.__build_surb_reply_path(target_node)

        surbid, surbkeytuple, nymtuple = self.__create_and_store_surb(nodes_routing_back, keys_nodes_back)
        header, delta = self.__create_forward_packet(nodes_routing, keys_nodes, nymtuple, payload)

        msg_bytes = pack_message(self._params, (header, delta))
        await self._peer.send(path[0], msg_bytes)

    def __build_forward_path(self, target_node):
        path = self.__build_path_to(self._node_id, target_node)
        return path, list(map(Nenc, path)), [self._key_store.get_y(nid) for nid in path]

    def __build_surb_reply_path(self, target_node):
        path = self.__build_path_to(target_node, self._node_id)
        return path, list(map(Nenc, path)), [self._key_store.get_y(nid) for nid in path]

    def __create_and_store_surb(self, routing, keys):
        surbid, surbkeytuple, nymtuple = create_surb(self._params, routing, keys, b"myself")
        self._surb_key_store[surbid] = surbkeytuple
        return surbid, surbkeytuple, nymtuple

    def __create_forward_packet(self, routing, keys, nymtuple, payload):
        return create_forward_message(self._params, routing, keys, b"peer-message", (nymtuple, payload))

    def __decrypt_surb(self, delta: bytes, id):
        if id in self._surb_key_store:
            key = self._surb_key_store[id]
            msg = receive_surb(self._params, key, delta)
            del self._surb_key_store[id]
            logging.debug(f"{self._node_id} resolved surb with message: {msg.decode()}")
        else:
            logging.warning(f"❌ Surb key for id:{id} not found in the store")
            return None
        
    async def __unpack_payload_and_send_surb(self, payload_bytes: bytes):
        try:
            nymtuple, payload = payload_bytes
            await self._incoming_queue.put(payload)

            reply_msg = f"Message received by node {self._node_id}".encode()
            header, delta = package_surb(self._params, nymtuple, reply_msg)
            msg_bytes = pack_message(self._params, (header, delta))
            first_hop = PFdecode(self._params, nymtuple[0])[1]
            await self._peer.send(first_hop, msg_bytes)
            logging.debug("Sent SURB-based reply.")

        except Exception as e:
            logging.error(f"Error handling surb: {e}")

    async def receive(self) -> bytes:
        return await self._incoming_queue.get()

    async def __handle_incoming(self, data: bytes):
        try:
            unpacked = self.__process_incoming(data)
            await self.__handle_routing_decision(*unpacked)
        except Exception as e:
            logging.warning(f"❌ Error in transport: {e}")

    def __process_incoming(self, data: bytes):
        param_dict = {(self._params.max_len, self._params.m): self._params}
        _, (header, delta) = unpack_message(param_dict, data)
        x = self._key_store.get_x(self._node_id)
        tag, info, (header, delta), mac_key = sphinx_process(self._params, x, header, delta)
        routing = PFdecode(self._params, info)
        return routing, header, delta, mac_key

    async def __handle_routing_decision(self, routing, header, delta, mac_key):
        if routing[0] == Relay_flag:
            await self._peer.send(routing[1], pack_message(self._params, (header, delta)))
        elif routing[0] == Dest_flag:
            dest, msg = receive_forward(self._params, mac_key, delta)
            await self.__unpack_payload_and_send_surb(msg)
        elif routing[0] == Surb_flag:
            self.__decrypt_surb(delta, routing[2])

    def __build_random_path(self):
        available_nodes = [nid for nid in self._peers if nid != self._node_id]
        return random.sample(available_nodes, min(self._max_hops, len(available_nodes)))

    def __build_path_to(self, start, target):
        intermediates = [nid for nid in self._peers if nid not in (start, target)]
        hops = random.sample(intermediates, min(self._max_hops - 1, len(intermediates)))
        return hops + [target]