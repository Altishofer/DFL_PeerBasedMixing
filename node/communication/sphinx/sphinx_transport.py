import asyncio
import logging
import secrets
from asyncio import QueueEmpty
import hashlib

from sphinxmix.SphinxClient import (
    Relay_flag, Dest_flag, Surb_flag,
    receive_forward, pack_message
)
from sphinxmix.SphinxParams import SphinxParams

from communication.sphinx.sphinx_router import SphinxRouter
from communication.tcp_server import TcpServer
from communication.packages import PackageHelper, PackageType
from utils.config_store import ConfigStore
from utils.exception_decorator import log_exceptions
from metrics.node_metrics import metrics, MetricField

class SphinxTransport:
    def __init__(self, node_id, port, peers, mixer):
        self._node_id = node_id
        self._port = port
        self._peers = peers
        self._mixer = mixer
        self._mixer.set_cover_generator(self._generate_cover_traffic)

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
        self._seen_hashes = set()
        # asyncio.create_task(self.resend_loop())

    def active_nodes(self):
        return len(self._peer.active_peers())

    async def close_all_connections(self):
        await self._peer.close_all_connections()

    def get_all_fragments(self):
        fragments = []
        while not self._incoming_queue.empty():
            try:
                fragments.append(self._incoming_queue.get_nowait())
            except QueueEmpty:
                break
        return fragments

    @log_exceptions
    async def start(self):
        asyncio.create_task(self._peer.start())
        await asyncio.sleep(5)
        await self._peer.connect_peers()
        await asyncio.sleep(10)
        await self._mixer.start()

    @log_exceptions
    def send_to_peers(self, message):
        peers = list(self._peer.active_peers())
        for peer_id in peers:
            self._mixer.add_outgoing_message(self.generate_path_and_send(message, peer_id, peers))
        return len(peers)

    @log_exceptions
    async def generate_path_and_send(self, message, target_node: int, peers: list):
        payload = PackageHelper.serialize_msg(message)
        path, msg_bytes = self.sphinx_router.create_forward_msg(target_node, payload, peers)
        logging.debug(f"path: {path}")
        await self._peer.send_to_peer(path[0], msg_bytes)

    @log_exceptions
    async def receive(self) -> bytes:
        return await self._incoming_queue.get()

    @log_exceptions
    async def resend_loop(self):
        while True:
            stale = self.sphinx_router.get_older_than(ConfigStore.resend_time)
            for fragment in stale:
                if not self._peer.is_active(fragment.target_node):
                    self.sphinx_router.remove_cache_for_disconnected(fragment.target_node)
                else:
                    await self.generate_path_and_send(fragment.payload, fragment.target_node, self._peer.active_peers())
                    metrics().increment(MetricField.RESENT)
            if len(stale) > 0:
                logging.warning(f"Resent {len(stale)} unacked fragments.")
            await asyncio.sleep(ConfigStore.resend_time)

    async def __handle_payload(self, payload):
        msg_hash = hashlib.sha256(payload).digest()
        if msg_hash in self._seen_hashes:
            logging.warning("Duplicate fragment dropped.")
            return
        self._seen_hashes.add(msg_hash)
        
        msg = PackageHelper.deserialize_msg(payload)
        if (msg["type"] == PackageType.MODEL_PART):
            await self._incoming_queue.put(msg)
        elif (msg["type"] == PackageType.COVER):
            logging.debug(f"Dropping cover package.")
        else:
            logging.warning(f"Unknown package type.")

    @log_exceptions
    async def __unpack_payload_and_send_surb(self, payload_bytes: bytes):
        nymtuple, payload = payload_bytes
        await self.__handle_payload(payload)
        msg_bytes, first_hop = self.sphinx_router.create_surb_reply(nymtuple)
        await self._peer.send_to_peer(first_hop, msg_bytes)
        logging.debug("Sent SURB-based reply.")

    @log_exceptions
    async def __handle_incoming(self, data: bytes, peer_id: int):
        metrics().increment(MetricField.TOTAL_MBYTES_RECEIVED, len(data) / 1048576)
        metrics().increment(MetricField.TOTAL_MSG_RECEIVED)
        try:
            unpacked = self.sphinx_router.process_incoming(data)
        except Exception as e:
            logging.warning(f"Failed to unpack incoming data: {e} from {peer_id}")
            return

        try:
            await self.__handle_routing_decision(*unpacked)
        except Exception as e:
            logging.exception(f"Error handling routing decision: {e} from {peer_id}")
            return
        
    @log_exceptions
    async def __handle_routing_decision(self, routing, header, delta, mac_key):
        if routing[0] == Relay_flag:
            relay = self._peer.send_to_peer(routing[1], pack_message(self._params, (header, delta)))
            await self._mixer.mix_relay(relay)
            metrics().increment(MetricField.FORWARDED)
        elif routing[0] == Dest_flag:
            metrics().increment(MetricField.FRAGMENTS_RECEIVED)
            _, msg = receive_forward(self._params, mac_key, delta)
            await self.__unpack_payload_and_send_surb(msg)
            metrics().increment(MetricField.SURB_REPLIED)
        elif routing[0] == Surb_flag:
            metrics().increment(MetricField.SURB_RECEIVED)
            self.sphinx_router.decrypt_surb(delta, routing[2])

    @log_exceptions
    async def _generate_cover_traffic(self, nr_bytes):
        target_node = secrets.choice(self._peer.active_peers())
        content = secrets.token_bytes(nr_bytes)
        payload = PackageHelper.format_cover_package(content)
        await self.generate_path_and_send(payload, target_node, self._peer.active_peers())