import asyncio
import logging
import pickle

from sphinxmix.SphinxClient import (
    Relay_flag, Dest_flag, Surb_flag,
    receive_forward, pack_message
)
from sphinxmix.SphinxParams import SphinxParams

from communication.sphinx.cache import Cache
from communication.sphinx.sphinx_router import SphinxRouter
from communication.tcp_server import TcpServer
from utils.config_store import ConfigStore
from utils.exception_decorator import log_exceptions
from metrics.node_metrics import metrics, MetricField



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

        self._cache = Cache()
        self._incoming_queue = asyncio.Queue()
        asyncio.create_task(self.resend_loop())

    @log_exceptions
    async def start(self):
        asyncio.create_task(self._peer.start())
        await asyncio.sleep(5)
        await self._peer.connect_peers()
        await asyncio.sleep(5)

    @log_exceptions
    async def send(self, json_payload: dict, target_node: int = None):
        # str_payload = pickle.dumps(json_payload)
        str_payload = json_payload
        # logging.info(f"sending {str_payload}, of type {type(str_payload)}")
        path, msg_bytes = self.sphinx_router.create_forward_msg(target_node, str_payload)
        await self._peer.send(path[0], msg_bytes)

    @log_exceptions
    async def receive(self) -> bytes:
        return await self._incoming_queue.get()

    @log_exceptions
    async def resend_loop(self):
        while True:
            stale = self._cache.get_older_than(ConfigStore.resend_time)
            for fragment in stale:
                await self.send(fragment.payload, fragment.target_node)
                logging.info(f"Resent message to node {fragment.target_node}")
            await asyncio.sleep(1)

    @log_exceptions
    async def __unpack_payload_and_send_surb(self, payload_bytes: bytes):
        nymtuple, payload = payload_bytes
        await self._incoming_queue.put(payload)
        msg_bytes, first_hop = self.sphinx_router.create_surb_reply(nymtuple)
        await self._peer.send(first_hop, msg_bytes)
        logging.debug("Sent SURB-based reply.")

    @log_exceptions
    async def __handle_incoming(self, data: bytes):
        metrics().increment(MetricField.FRAGMENT_RECEIVED)
        metrics().increment(MetricField.BYTES_RECEIVED, len(data))
        unpacked = self.sphinx_router.process_incoming(data)
        await self.__handle_routing_decision(*unpacked)

    @log_exceptions
    async def __handle_routing_decision(self, routing, header, delta, mac_key):
        if routing[0] == Relay_flag:
            metrics().increment(MetricField.FRAGMENTS_FORWARDED)
            await self._peer.send(routing[1], pack_message(self._params, (header, delta)))
        elif routing[0] == Dest_flag:
            dest, msg = receive_forward(self._params, mac_key, delta)
            await self.__unpack_payload_and_send_surb(msg)
        elif routing[0] == Surb_flag:
            self.sphinx_router.decrypt_surb(delta, routing[2])
