import random
import logging

from sphinxmix.SphinxClient import (
    create_forward_message, PFdecode,
    Nenc, pack_message, unpack_message,
    create_surb, package_surb, receive_surb
)
from sphinxmix.SphinxNode import sphinx_process

from communication.sphinx.cache import Cache
from node.communication.sphinx.key_store import KeyStore
from utils.config_store import ConfigStore
from utils.exception_decorator import log_exceptions


class SphinxRouter:
    def __init__(self, node_id, peers, params):
        self._max_hops = ConfigStore.max_hops
        self._node_id = node_id
        self._peers = peers
        self._params = params
        self.cache = Cache()
        self._key_store = KeyStore()

        self._surb_key_store = {}

    @log_exceptions
    def create_forward_msg(self, target_node, payload):
        path, nodes_routing, keys_nodes = self.build_forward_path(target_node)
        backward_path, nodes_routing_back, keys_nodes_back = self.build_surb_reply_path(target_node)

        surbid, surbkeytuple, nymtuple = self.create_and_store_surb(nodes_routing_back, keys_nodes_back)
        header, delta = self.create_forward_packet(nodes_routing, keys_nodes, nymtuple, payload)
        msg_bytes = pack_message(self._params, (header, delta))
        self.cache.new_fragment(surbid, surbkeytuple, target_node, payload)
        return path, msg_bytes

    @log_exceptions
    def create_surb_reply(self, nymtuple):
        reply_msg = f"Message received by node {self._node_id}".encode()
        header, delta = package_surb(self._params, nymtuple, reply_msg)
        msg_bytes = pack_message(self._params, (header, delta))
        first_hop = PFdecode(self._params, nymtuple[0])[1]
        return msg_bytes, first_hop

    @log_exceptions
    def build_forward_path(self, target_node):
        path = self._build_path_to(self._node_id, target_node)
        return path, list(map(Nenc, path)), [self._key_store.get_y(nid) for nid in path]

    @log_exceptions
    def build_surb_reply_path(self, target_node):
        path = self._build_path_to(target_node, self._node_id)
        return path, list(map(Nenc, path)), [self._key_store.get_y(nid) for nid in path]

    @log_exceptions
    def create_and_store_surb(self, routing, keys):
        surbid, surbkeytuple, nymtuple = create_surb(self._params, routing, keys, b"myself")
        self._surb_key_store[surbid] = surbkeytuple
        return surbid, surbkeytuple, nymtuple

    @log_exceptions
    def create_forward_packet(self, routing, keys, nymtuple, payload):
        return create_forward_message(self._params, routing, keys, b"peer-message", (nymtuple, payload))

    @log_exceptions
    def decrypt_surb(self, delta: bytes, surb_id):
        key = self.cache.received_surb(surb_id)

        key = self._surb_key_store[surb_id]
        msg = receive_surb(self._params, key, delta)
        logging.debug(f"{self._node_id} resolved surb with message: {msg.decode()}")
        return msg

    @log_exceptions
    def _build_path_to(self, start, target):
        intermediates = [nid for nid in self._peers if nid not in (start, target)]
        hops = random.sample(intermediates, min(self._max_hops - 1, len(intermediates)))
        return hops + [target]

    @log_exceptions
    def process_incoming(self, data: bytes):
        param_dict = {(self._params.max_len, self._params.m): self._params}
        _, (header, delta) = unpack_message(param_dict, data)
        x = self._key_store.get_x(self._node_id)
        tag, info, (header, delta), mac_key = sphinx_process(self._params, x, header, delta)
        routing = PFdecode(self._params, info)
        return routing, header, delta, mac_key

