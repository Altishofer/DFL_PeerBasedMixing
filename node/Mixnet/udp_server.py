import asyncio
import logging
import socket
import struct
import time
import uuid
import random
from collections import defaultdict
from typing import Dict, List, Tuple

import uvloop

from nebula.core.network.udp_stack import MixNet
from nebula.core.network.udp_stack.packet_header import PacketHeader
from nebula.core.network.udp_stack.udp_connection import UdpConnection
from nebula.core.network.udp_stack.udp_fragment_buffer import FragmentBuffer
from nebula.core.network.udp_stack.udp_protocol import UdpProtocol
from nebula.core.network.udp_stack.udp_stats_manager import StatsManager
from nebula.core.network.udp_stack.udp_writer import UdpWriter
from nebula.core.network.udp_stack.udp_reader import UdpReader
from nebula.core.network.udp_stack.udp_config import UdpConfig


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.basicConfig(level=logging.INFO) # , force=True)


class UdpServer:

    def __init__(self, host_ip, host_port, node_id, handle_connection):
        # logging.debug("⚡️ UdpServer.__init__ called")

        self._host_ip = str(host_ip)
        self._host_port = int(host_port)
        self._node_id = node_id

        self._transport = None
        self.server_started = asyncio.Event()

        self._handle_connection = handle_connection
        self._in_queue = asyncio.Queue(maxsize=50_000)
        self._mix_queue = asyncio.Queue(maxsize=50_000)
        self._send_queue = asyncio.Queue(maxsize=50_000)
        self._udp_protocol = UdpProtocol(self._handle_connection, self.server_started, self)

        self._udp_connections: dict[int, UdpConnection] = {}
        self._udp_connections_lock = asyncio.Lock()

        self._udp_fragments = FragmentBuffer()
        self._stats = StatsManager()

        self._message_handler_lock = asyncio.Lock()
        self._tasks: list[asyncio.Task] = []

    async def start_server(self):
        # logging.debug("⚡️ UdpServer.start_server called")
        loop = asyncio.get_running_loop()
        try:
            self._transport, _ = await loop.create_datagram_endpoint(
                lambda: self._udp_protocol,
                local_addr=(self._host_ip, self._host_port),
                family=socket.AF_INET,
                allow_broadcast=True
            )
            await self.server_started.wait()

            self._tasks = [
                asyncio.create_task(self._mixing()),
                *[asyncio.create_task(self._process_packets()) for _ in range(4)],
                asyncio.create_task(self._send_loop()),
                asyncio.create_task(self._periodic_push_ready_messages())
            ]

            # logging.debug("⚡️ UdpServer.start_server completed")
        except:
            logging.error(f"⚡️ UdpServer.start_server Failed to start UDP server")

    async def _send_loop(self):
        while True:
            packet, addr = await self._send_queue.get()
            try:
                self._transport.sendto(packet, addr)
            except Exception:
                logging.exception("⚡️ UdpServer._send_loop failed")
            finally:
                await asyncio.sleep(UdpConfig.SLEEP_BETWEEN_MSG)


    async def get_reader_writer(self, ip, port, identifier=None):
        # logging.debug(f"⚡️ UdpServer.get_reader_writer called for {ip}:{port}")
        addr = (str(ip), int(port))
        if identifier is None:
            identifier = uuid.uuid4().int % (2**32)
        nr = UdpReader(addr, identifier)
        nw = UdpWriter(addr, self, identifier)
        async with self._udp_connections_lock:
            self._udp_connections[identifier] = UdpConnection(reader=nr, writer=nw)

        # logging.debug(f"⚡️ UdpServer.get_reader_writer returning new reader/writer for {ip}:{port}")
        return nr, nw

    async def send_message(self, message, addr):
        # logging.debug(f"⚡️ UdpServer.send_message called to {addr}")
        route = await self._select_route(addr)
        next_hop, wrapped = MixNet.onion_wrap(message, route, self._host_ip, self._host_port)
        self._send_queue.put_nowait((wrapped, next_hop))
        # logging.debug(f"⚡️ UdpServer.send_message sent {len(wrapped)} bytes to {next_hop}")

    async def print_stats(self):
        # logging.debug(f"⚡️ UdpServer.log_statistics add:{self._host_ip}, node_id:{self._node_id}\n")
        self._stats.print_stats()

    async def _select_route(self, final_destination):
        mixnet_nodes = [node for node in self._stats.all_addresses() if node != final_destination]
        intermediate_hops = random.sample(mixnet_nodes, k=min(UdpConfig.N_HOPS, len(mixnet_nodes))) if mixnet_nodes else []
        route = intermediate_hops + [final_destination]
        # logging.debug(f"⚡️ UdpServer.select_route Sending msg for {final_destination} over {route}")
        return route

    def _is_me(self, addr):
        return addr == (self._host_ip, self._host_port)

    async def _handle_onion_routing(self, data):
        addr, remainder = MixNet.onion_peel(data)
        if addr == ("0.0.0.0", 0):
            original_sender, remainder = MixNet.onion_peel(remainder)
            # logging.debug(f"⚡️ UdpServer.handle_onion_routing Received msg over MixNet by {original_sender}")
            return original_sender, remainder

        if not self._is_me(addr):
            self._stats.forwarded_message(addr)
            self._mix_queue.put_nowait((addr, remainder))
            return None, None

        logging.error(f"⚡️ UdpServer.handle_onion_routing Unexpected state")
        return None, None

    async def _mixing(self):
        while True:
            await asyncio.sleep(UdpConfig.SLEEP_MIX_DELAY)
            batch = []
            try:
                batch.append(await self._mix_queue.get())
            except asyncio.CancelledError:
                # logging.debug(f"⚡️ UdpServer.mix_forward_loop Failed")
                return
            while not self._mix_queue.empty() and len(batch) < 100:
                batch.append(self._mix_queue.get_nowait())

            random.shuffle(batch)
            for next_addr, forward_packet in batch:
                self._send_queue.put_nowait((forward_packet, next_addr))

    async def close(self):
        # logging.debug("⚡️ UdpServer.close called")
        if self._transport:
            self._transport.close()
            self._transport = None
            logging.debug("⚡️ UdpServer.close completed")

    async def datagram_received(self, packet, addr):
        # logging.debug(f"⚡️ UdpServer.datagram_received called from {addr}")
        self._in_queue.put_nowait((packet, addr))

    async def _process_packets(self):
        # logging.debug("⚡️ UdpServer._process_packets started")
        while True:
            packet, addr = await self._in_queue.get()
            try:
                # logging.debug(f"⚡️ UdpServer._process_packets got packet from {addr}")
                await self._handle_packet(packet, addr)
            except Exception as e:
                logging.error(f"⚡️ UdpServer._process_packets Failed to process packet from {addr}: {e}", exc_info=True)

    async def _handle_packet(self, packet, last_hop):
        arrival_time = time.time()

        addr, after_onion = await self._handle_onion_routing(packet)
        if after_onion is None or addr is None:
            # logging.debug("⚡️ UdpServer._handle_packet ONION message was forwarded to next hop")
            return

        if len(after_onion) < 32:
            logging.error("⚡️ UdpServer._handle_packet packet too short after peeling")
            return

        addr = (str(addr[0]), int(addr[1]))

        try:
            header = PacketHeader.parse(after_onion)
        except ValueError as e:
            logging.error(f"⚡️ UdpServer._handle_packet invalid packet from {addr}: {e}")
            return

        sid = int(header.sid)
        dk = sid
        async with self._udp_connections_lock:
            exists = dk in self._udp_connections
        if not exists:
            r, w = await self.get_reader_writer(addr[0], addr[1], sid)
            asyncio.create_task(self._handle_connection(r, w))
        async with self._udp_connections_lock:
            r = self._udp_connections[dk].reader
            w = self._udp_connections[dk].writer

        # encoding an ack
        if int(header.total) == 0:
            await self._read_ack(header, w, addr)
        else:
            # gopfertami, add ack even if already received, ack was lost
            await w.add_ack_to_queue(header.seq, header.idx)
            await self._udp_fragments.handle_fragment(r, sid, header, arrival_time, self._stats, addr, w)

    async def _read_ack(self, header, writer, addr):
        ack_count, = struct.unpack("!I", header.payload[:4])
        offset = 4
        for _ in range(ack_count):
            seq_num, frag_num = struct.unpack("!II", header.payload[offset:offset + 8])
            offset += 8
            await writer.received_ack(seq_num, frag_num)

        self._stats.lost_fragments(addr, writer.total_lost_fragments())
        self._stats.ack_messages(addr, writer.total_sent_cumulative_ack())

    async def _periodic_push_ready_messages(self, interval=0.5):
        while True:
            try:
                await self._push_ready_messages()
            except:
                logging.exception("⚡️ Error in push_ready_messages loop")
            await asyncio.sleep(interval)

    async def _push_ready_messages(self):
        ready_packets = []

        async for sid, seq, seq_data in self._udp_fragments.ready_sequences():

            full = memoryview(seq_data.assembled)[:seq_data.size]
            pkt = struct.pack("!IIII", seq, sid, seq_data.total, seq_data.total - 1) + full
            ready_packets.append((sid, seq, pkt))

        if not ready_packets:
            return

        ready_packets.sort(key=lambda x: (x[0], x[1]))
        grouped_by_sid: Dict[int, List[Tuple[int, bytes]]] = defaultdict(list)
        for sid, seq, packet in ready_packets:
            grouped_by_sid[sid].append((seq, packet))

        async with self._message_handler_lock, self._udp_connections_lock:
            for sid, packets in grouped_by_sid.items():
                connection = self._udp_connections.get(sid)
                if connection is None:
                    continue

                r = self._udp_connections[sid].reader
                r_addr = r.get_addr()
                next_seq = await r.get_next_seq()

                for seq, pkt in packets:
                    if seq == next_seq:
                        await r.add_message(pkt, seq)
                        await self._udp_fragments.delete_seq(sid, seq)
                        # logging.debug(f"⚡️ push_ready_messages Queued the correct sequence {seq} for {r_addr}")
                    elif seq < next_seq:
                        await self._udp_fragments.delete_seq(sid, seq)
                        # logging.debug(f"⚡️ push_ready_messages Dropping seq {seq} since < {next_seq} for {r_addr}")
                    elif seq > next_seq:
                        pass
                        # logging.debug(f"⚡️ push_ready_messages Skipping future seq {seq} > {next_seq} for {r_addr}")
