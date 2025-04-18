import asyncio
import logging
import struct
import time
import hashlib
import random

from nebula.core.network.udp_stack.packet_header import PacketHeader
from nebula.core.network.udp_stack.udp_config import UdpConfig
from nebula.core.network.udp_stack.udp_message_cache import MessageCache


class UdpWriter:
    def __init__(self, address, outer_server, sender_id):
        # logging.debug("⚡️ UdpWriter.__init__ called")
        self.address = address
        self.outer_server = outer_server
        self.sequence_number = -1
        self.total_fragments = 0
        self.sender_id = int(sender_id)
        self.rtt = UdpConfig.INITIAL_RTT
        self.resend_counter = 0
        self.ack_counter = 0
        self.sent_ack_counter = 0
        self.periodic_ack_send_task = asyncio.create_task(self.periodic_cumulative_ack())
        self.message_cache = MessageCache()
        self.periodic_resend_task = asyncio.create_task(self.periodic_resend())
        self.dummy_bytes = b"\x00\x00\x00\x00"
        self.ack_message_queue = asyncio.Queue(100_000)
        self.ack_message_queue_lock = asyncio.Lock()

    async def __get_all_acks(self):
        items = []
        async with self.ack_message_queue_lock:
            while not self.ack_message_queue.empty():
                items.append(self.ack_message_queue.get_nowait())
        return items

    async def add_ack_to_queue(self, sequence_number, fragment_number):
        # # logging.debug(f"⚡️ UdpWriter.add_ack_to_queue for seq={sequence_number} frag={fragment_number} {self.address}")
        async with self.ack_message_queue_lock:
            try:
                self.ack_message_queue.put_nowait((sequence_number, fragment_number))
            except asyncio.QueueFull:
                logging.error("⚡️ UdpServer.datagram_received queue is full")
                raise

    async def send_delayed_cumulative_ack(self):
        acks = await self.__get_all_acks()
        ack_count = len(acks)
        if not ack_count:
            # # logging.debug(f"⚡️ No ACKs to send for {self.address}")
            return

        payload = struct.pack("!I", len(acks))
        for (seq, frag) in acks:
            payload += struct.pack("!II", seq, frag)

        packet = PacketHeader.build(0, self.sender_id, 0, 0, payload)
        await self.outer_server.send_message(packet, self.address)
        self.sent_ack_counter += 1
        # # logging.debug(f"⚡️ Sent delayed ACK with {len(acks)} entries to {self.address}")

    async def received_ack(self, sequence_number, fragment_idx):
        # # logging.debug(f"⚡️ UdpWriter.received_ack seq={sequence_number}, frag={fragment_idx} from {self.address}")
        st = await self.message_cache.remove_acknowledged(sequence_number, fragment_idx)
        if st is not None:
            sample_rtt = time.time() - st
            self.rtt = (self.rtt * self.ack_counter + sample_rtt) / (self.ack_counter + 1)
            self.ack_counter += 1
            # # logging.debug(f"⚡️ UdpWriter.received_ack updated rtt={self.rtt}, ack_counter={self.ack_counter}")

    async def write(self, data: bytes, send_timeout=60):
        try:
            await asyncio.wait_for(
                self.split_and_send(data),
                timeout=send_timeout
            )
        except asyncio.TimeoutError:
            await self.outer_server.print_stats()
            logging.error(f"⚡️ UdpWriter.write Timeout sending sequence to {self.address}")
        except Exception as e:
            await self.outer_server.print_stats()
            logging.exception(f"⚡️ UdpWriter.write Error sending sequence to {self.address}: {e}")

    async def split_and_send(self, data:bytes):
        # # logging.debug(f"⚡️ UdpWriter.write called for {self.address}")

        if not isinstance(data, bytes):
            logging.error(f"⚡️ UdpWriter.write was called with type {type(data)} instead of bytes")
            return

        self.sequence_number += 1
        tl = len(data)
        nf = (tl // UdpConfig.MAX_UDP_PAYLOAD) + (1 if tl % UdpConfig.MAX_UDP_PAYLOAD else 0)
        self.total_fragments += nf
        for idx in range(nf):
            while await self.message_cache.inflight() >= UdpConfig.SEND_WINDOW_SIZE:
                # # logging.debug(f"⚡️ UdpWriter.write inflight full {await self.message_cache.inflight()} >= {UdpConfig.SEND_WINDOW_SIZE}, sleeping")
                await asyncio.sleep(UdpConfig.WAIT_WINDOW_FULL)

            start = idx * UdpConfig.MAX_UDP_PAYLOAD
            end = start + UdpConfig.MAX_UDP_PAYLOAD
            frag = data[start:end]
            packet = PacketHeader.build(self.sequence_number, self.sender_id, nf, idx, frag)
            await self.message_cache.add(self.sequence_number, idx, packet)

            try:
                await self.outer_server.send_message(packet, self.address)
            except:
                logging.error(f"⚡️ UdpWriter.write ERROR sending {nf} fragments to {self.address}")
        # logging.debug(f"⚡️ UdpWriter.write finished sending {nf} fragments to {self.address}")

    def loss_ratio(self):
        if self.total_fragments == 0:
            return 0.0
        return self.resend_counter / self.total_fragments

    async def periodic_cumulative_ack(self):
        while True:
            interval = max(min(self.rtt * UdpConfig.ACK_RTT_FACTOR, UdpConfig.MAX_WAIT_ACK), UdpConfig.MIN_WAIT_ACK)
            await asyncio.sleep(interval)
            await self.send_delayed_cumulative_ack()

    async def periodic_resend(self):
        while True:
            interval = max(min(self.rtt * UdpConfig.RESEND_RTT_FACTOR, UdpConfig.MAX_WAIT_RESEND), UdpConfig.MIN_WAIT_RESEND)
            await asyncio.sleep(interval)
            now = time.time()

            # logging.debug(f"⚡️ cache for {self.address} = {await self.message_cache.n_sequences()}:{await self.message_cache.n_fragments()}")

            for seq, idx, packet, last_sent in await self.message_cache.all():
                if now - last_sent >= interval:
                    self.resend_counter += 1
                    try:
                        await self.outer_server.send_message(packet, self.address)
                        await self.message_cache.update_sent_time(seq, idx)
                        # logging.debug(f"⚡️ Resent seq={seq}, idx={idx} to {self.address}")
                    except Exception as e:
                        logging.error(f"⚡️ Failed to resend seq={seq}, idx={idx} to {self.address}: {e}")

    async def get_not_acked(self):
        return await self.message_cache.inflight()

    async def close(self):
        # logging.debug(f"⚡️ UdpWriter.close called for {self.address}")
        pass

    def get_extra_info(self, info_key: str):
        return self.address

    async def send_status(self, status):
        # logging.debug(f"⚡️ UdpWriter.send_status called for {self.address}")
        await self.write(self.dummy_bytes + f"{status}".encode())

    async def send_id(self, node_id):
        # logging.debug(f"⚡️ UdpWriter.send_id called for {self.address}")
        await self.write(self.dummy_bytes + f"{node_id}".encode())

    async def send_direct(self, direct):
        # logging.debug(f"⚡️ UdpWriter.send_direct called for {self.address}")
        await self.write(self.dummy_bytes + f"{direct}".encode())

    def total_lost_fragments(self):
        return self.resend_counter

    def total_ack_counter(self):
        return self.ack_counter

    def total_sent_cumulative_ack(self):
        return self.sent_ack_counter

    def get_rtt(self):
        return self.rtt
