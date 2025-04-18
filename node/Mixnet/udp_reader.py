import asyncio
import heapq
import logging
import struct


class UdpReader:
    def __init__(self, addr, identifier):
        # logging.debug("⚡️ UdpReader.__init__ called")
        self.address = addr
        self.identifier = identifier
        self.message_heap = []
        self.heap_lock = asyncio.Lock()
        self.condition = asyncio.Condition(self.heap_lock)
        self.next_seq = 0
        self.next_seq_lock = asyncio.Lock()

    def get_addr(self):
        return self.address

    async def get_next_seq(self):
        async with self.next_seq_lock:
            return self.next_seq

    async def inc_seq(self):
        async with self.next_seq_lock:
            self.next_seq += 1

    async def add_message(self, packet, seq):
        # logging.debug(f"⚡️ UdpReader.add_message called for {self.address}")
        if len(packet) < 4:
            logging.error("⚡️ UdpReader.add_message packet too short")
            return

        async with self.next_seq_lock:
            if seq < self.next_seq:
                logging.error("⚡️ UdpReader.add_message Pushing past seq should NOT be possible.")
                return
            if seq > self.next_seq:
                logging.error("⚡️ UdpReader.add_message Pushing future seq should NOT be possible.")
                return
            if seq == self.next_seq:
                # logging.debug("⚡️ UdpReader.add_message Received expected seq for client.")
                self.next_seq += 1

            sn, si, tf, fi = struct.unpack("!IIII", packet[:16])
            pl = packet[16:]
            async with self.condition:
                heapq.heappush(self.message_heap, (sn, pl))
                self.condition.notify(1)

        # logging.debug(f"⚡️ UdpReader.add_message stored sequence {sn} for {self.address}")

    async def read_frame(self) -> bytes:
        # logging.debug(f"⚡️ UdpReader.read_frame waiting for data from {self.address}")
        async with self.condition:
            while not self.message_heap:
                await self.condition.wait()
            sn, pl = heapq.heappop(self.message_heap)
            # logging.debug(f"⚡️ UdpReader.read_frame returning sequence {sn} for {self.address}")
            return pl[4:]

    async def readline(self) -> str:
        # logging.debug(f"⚡️ UdpReader.readline called for {self.address}")
        pl = await self.read_frame()
        return pl.decode("utf-8").strip()
