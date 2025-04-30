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
from key_store import KeyStore

from tcp_server import TCP_Server

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

        self._peer = TCP_Server(
            node_id=node_id,
            port=port,
            peers=peers,
            packet_size=self._packet_size,
            message_handler=self.__handle_incoming
        )

        self._incoming_queue = asyncio.Queue()
        self._surb_store = {}

    async def start(self):
        asyncio.create_task(self._peer.start())

    async def send(self, payload: bytes, target_node: int = None):
        path = self.__build_path_to(self._node_id, target_node)
        logging.debug(f"Path to {target_node} from {self._node_id}")

        nodes_routing = list(map(Nenc, path))
        keys_nodes = [self._key_store.get_y(nid) for nid in path]

        backward_path = self.__build_path_to(target_node, self._node_id)
        nodes_routing_back = list(map(Nenc, backward_path))
        keys_nodes_back = [self._key_store.get_y(nid) for nid in backward_path]
        
        surbid, surbkeytuple, nymtuple = create_surb(self._params, nodes_routing_back, keys_nodes_back, b"myself")
        self._surb_store[surbid] = surbkeytuple
    
        header, delta = create_forward_message(self._params, nodes_routing, keys_nodes, b"peer-message", (nymtuple, payload))
        msg_bytes = pack_message(self._params, (header, delta))

        first_hop = path[0]
        await self._peer.send(first_hop, msg_bytes)

    def __resolve_surb(self, delta: bytes, id):
        if (id in self._surb_store):
            key = self._surb_store[id]
            msg = receive_surb(self._params, key, delta)
            del self._surb_store[id]
            logging.info(f"Node {self._node_id} resolved surb with message: {msg.decode()}")
        else:
            logging.warning(f"❌ Surb {id} not found in the store")
            return None
        
    async def __handle_surb(self, payload_bytes: bytes):
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
            param_dict = {(self._params.max_len, self._params.m): self._params}
            unpacked_msg = unpack_message(param_dict, data)
            _, (header, delta) = unpacked_msg
            x = self._key_store.get_x(self._node_id)
            tag, info, (header, delta), mac_key = sphinx_process(self._params, x, header, delta)
            routing = PFdecode(self._params, info)

            if routing[0] == Relay_flag:
                _, next_id = routing
                msg = pack_message(self._params, (header, delta))
                await self._peer.send(next_id, msg)
            elif routing[0] == Dest_flag:
                dest, msg = receive_forward(self._params, mac_key, delta)
                await self.__handle_surb(msg)
            elif routing[0] == Surb_flag:
                _, dest, myid = routing
                self.__resolve_surb(delta, myid)

        except Exception as e:
            logging.warning(f"❌ Error in transport: {e}")

    def __build_random_path(self):
        available_nodes = [nid for nid in self._peers if nid != self._node_id]
        return random.sample(available_nodes, min(self._max_hops, len(available_nodes)))

    def __build_path_to(self, start, target):
        intermediates = [nid for nid in self._peers if nid not in (start, target)]
        hops = random.sample(intermediates, min(self._max_hops - 1, len(intermediates)))
        return hops + [target]