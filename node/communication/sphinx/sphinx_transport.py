import asyncio
import hashlib
import logging
import secrets
from asyncio import QueueEmpty

from sphinxmix.SphinxClient import (
    Relay_flag, Dest_flag, Surb_flag,
    receive_forward, pack_message
)
from sphinxmix.SphinxParams import SphinxParams

from communication.packages import PackageHelper, PackageType
from communication.sphinx.sphinx_router import SphinxRouter
from communication.tcp_server import TcpServer
from metrics.node_metrics import metrics, MetricField
from utils.config_store import ConfigStore
from utils.exception_decorator import log_exceptions
from communication.mixing import Mixer


class SphinxTransport:
    def __init__(self, node_id, port, peers, node_config: ConfigStore):
        self._node_id = node_id
        self._port = port
        self._peers = peers
        self._mixer = Mixer(self.send_cover_traffic)
        self._node_config = node_config
        self.n_fragments_per_model = None  # will be set dynamically once number is determined

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
        asyncio.create_task(self.resend_loop())
        self._cover_stash = []

    @log_exceptions
    async def received_all_expected_fragments(self):
        total_expected = self.active_nodes() * self.n_fragments_per_model
        if total_expected == 0:
            logging.warning("No active nodes, cannot determine expected fragments.")
            return True
        received_packets = self._incoming_queue.qsize()
        percentage_received = (received_packets / total_expected) * 100
        logging.info(f"Received {percentage_received:.2f}% of packets")
        return received_packets >= total_expected

    @log_exceptions
    async def transport_all_acked(self):
        return await self.sphinx_router.router_all_acked()

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

    def push_unexpected_to_queue(self, fragment):
        self._incoming_queue.put_nowait(fragment)
        logging.warning("Received unexpected fragment, pushing back to queue.")

    @log_exceptions
    async def start(self):
        asyncio.create_task(self._peer.start())
        await asyncio.sleep(5)
        await self._peer.connect_peers()
        if ConfigStore.cache_covers:
            asyncio.create_task(self._generate_cover_traffic_loop())
        await asyncio.sleep(5)
        await self._mixer.start()
        await asyncio.sleep(10)

    @log_exceptions
    async def send_to_peers(self, message):
        peers = list(self._peer.active_peers())
        for peer_id in peers:
            path, msg_bytes = await self.generate_path(message, peer_id, False)
            update_metrics_task = self.increment_metric_task(MetricField.FRAGMENTS_SENT)
            send_msg_task = self.create_send_message_task(path, msg_bytes)
            await asyncio.sleep(0.0)
            await self._mixer.queue_item(send_msg_task, update_metrics_task)
        return len(peers)

    def create_send_message_task(self, path, msg_bytes):
        async def send_message():
            await self.send(path, msg_bytes)

        return send_message

    def increment_metric_task(self, metric_field):
        def update_metrics():
            metrics().increment(metric_field)

        return update_metrics
    
    async def generate_path(self, message, target_node: int, cover: bool, serialize: bool = True):
        peers = list(self._peer.active_peers())
        payload = message
        if serialize:
            payload = PackageHelper.serialize_msg(message)
        path, msg_bytes = await self.sphinx_router.create_forward_msg(target_node, payload, peers, cover)
        return path, msg_bytes

    async def generate_path_and_send(self, message, target_node: int, cover: bool, serialize: bool = True):
        path, msg_bytes = await self.generate_path(message, target_node, cover, serialize)
        await self.send(path, msg_bytes)

    @log_exceptions
    async def send(self, path, msg_bytes):
        await self._peer.send_to_peer(path[0], msg_bytes)

    @log_exceptions
    async def receive(self) -> bytes:
        return await self._incoming_queue.get()

    async def resend_loop(self):
        while True:
            stale = self.sphinx_router.get_older_than(ConfigStore.resend_time)
            for fragment in stale:
                if not self._peer.is_active(fragment.target_node):
                    self.sphinx_router.remove_cache_for_disconnected(fragment.target_node)
                else:
                    send_message_task = self.create_resend_task(fragment)
                    update_metrics_task = self.increment_metric_task(MetricField.RESENT)
                    await self._mixer.queue_item(send_message_task, update_metrics_task)
            if stale:
                logging.warning(f"Resent {len(stale)} unacked fragments.")
            await asyncio.sleep(5)

    def create_resend_task(self, fragment):
        async def send_message():
            await self.generate_path_and_send(
                fragment.payload,
                fragment.target_node,
                serialize=False,
                cover=fragment.cover
            )

        return send_message

    async def __handle_payload(self, payload):

        msg = PackageHelper.deserialize_msg(payload)
        is_cover = msg["type"] == PackageType.COVER

        if not is_cover:

            msg_hash = hashlib.sha256(payload).digest()
            if msg_hash in self._seen_hashes:
                logging.debug("Duplicate fragment dropped.")
                metrics().increment(MetricField.RECEIVED_DUPLICATE_MSG)
                return is_cover

            self._seen_hashes.add(msg_hash)
            metrics().increment(MetricField.FRAGMENTS_RECEIVED)
            await self._incoming_queue.put(msg)
            return is_cover

        else:
            metrics().increment(MetricField.COVERS_RECEIVED)
            # logging.debug(f"Dropping cover package.")

        return is_cover

    @log_exceptions
    async def __unpack_payload(self, payload_bytes: bytes):
        nymtuple, payload = payload_bytes
        is_cover = await self.__handle_payload(payload)
        return nymtuple, is_cover

    async def __send_surb(self, nymtuple):
        msg_bytes, first_hop = self.sphinx_router.create_surb_reply(nymtuple)
        # logging.debug("Sent SURB-based reply.")
        await self._peer.send_to_peer(first_hop, msg_bytes)

    @log_exceptions
    async def __handle_incoming(self, data: bytes, peer_id: int):
        metrics().increment(MetricField.TOTAL_MBYTES_RECEIVED, len(data) / 1048576)
        metrics().increment(MetricField.TOTAL_MSG_RECEIVED)
        try:
            unpacked = await self.sphinx_router.process_incoming(data)
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
            send_message_task = self.create_forward_task(routing[1], header, delta)
            update_metrics_task = self.increment_metric_task(MetricField.FORWARDED)
            await self._mixer.queue_item(send_message_task, update_metrics_task)

        elif routing[0] == Dest_flag:
            _, msg = receive_forward(self._params, mac_key, delta)
            nymtuple, is_cover = await self.__unpack_payload(msg)
            if is_cover: return
            send_message_task = self.create_surb_reply_task(nymtuple)
            update_metrics_task = self.increment_metric_task(MetricField.SURB_REPLIED)
            await self._mixer.queue_item(send_message_task, update_metrics_task)

        elif routing[0] == Surb_flag:
            metrics().increment(MetricField.SURB_RECEIVED)
            self.sphinx_router.decrypt_surb(delta, routing[2])
        else:
            logging.info(f"Unexpected routing flag: {routing[0]} from {routing[1]}")

    def create_forward_task(self, routing, header, delta):
        async def send_message():
            msg = pack_message(self._params, (header, delta))
            await self._peer.send_to_peer(routing, msg)

        return send_message

    def create_surb_reply_task(self, nymtuple):
        async def send_message():
            await self.__send_surb(nymtuple)

        return send_message

    @log_exceptions
    async def generate_cover_traffic(self):
        if len(self._peer.active_peers()) == 0:
            return
        target_node = secrets.choice(self._peer.active_peers())
        content = secrets.token_bytes(ConfigStore.nr_cover_bytes)
        payload = PackageHelper.format_cover_package(content)
        path, msg_bytes = await self.generate_path(payload, target_node, cover=True)
        return path, msg_bytes
    
    async def _generate_cover_traffic_loop(self):
        while True:
            if len(self._cover_stash) < 10 * ConfigStore.mix_outbox_size and len(self._peer.active_peers()) != 0:
                path, msg_bytes = await self.generate_cover_traffic()
                cover = self.create_send_message_task(path, msg_bytes)
                self._cover_stash.append(cover)
            await asyncio.sleep(ConfigStore.mix_mu)

    async def send_cover_traffic(self):
        if len(self._cover_stash) > 0:
            send_cover = self._cover_stash.pop()
        else:
            path, msg_bytes = await self.generate_cover_traffic()
            send_cover = self.create_send_message_task(path, msg_bytes)
        await send_cover()
