import logging
from collections import defaultdict
import asyncio

from nebula.core.network.udp_stack.udp_config import UdpConfig
from nebula.core.network.udp_stack.udp_connection_stats import ConnectionStats

class FragmentBuffer:
    def __init__(self):
        # logging.debug("⚡️ FragmentBuffer.__init__ called")
        self._buffers = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def in_keys(self, sender_id):
        async with self._lock:
            result = sender_id in self._buffers
        # logging.debug(f"⚡️ FragmentBuffer.in_keys({sender_id}) -> {result}")
        return result

    async def exists(self, sender_id, seq_id):
        async with self._lock:
            result = sender_id in self._buffers and seq_id in self._buffers[sender_id]
        # logging.debug(f"⚡️ FragmentBuffer.exists({sender_id}, {seq_id}) -> {result}")
        return result

    async def delete_seq(self, sender_id, seq_id):
        async with self._lock:
            if sender_id in self._buffers and seq_id in self._buffers[sender_id]:
                del self._buffers[sender_id][seq_id]
                if not self._buffers[sender_id]:
                    del self._buffers[sender_id]
                # logging.debug(f"⚡️ FragmentBuffer.delete_seq({sender_id}, {seq_id}) -> deleted")
            else:
                logging.debug(f"⚡️ FragmentBuffer.delete_seq({sender_id}, {seq_id}) -> not found")

    async def get_or_create(self, sid: int, seq: int, total: int, start_time: float) -> ConnectionStats:
        async with self._lock:
            created = False
            if seq not in self._buffers[sid]:
                self._buffers[sid][seq] = ConnectionStats(total, start_time)
                created = True
            result = self._buffers[sid][seq]
        # logging.debug(f"⚡️ FragmentBuffer.get_or_create({sid}, {seq}, {total}, {start_time}) -> created={created}")
        return result

    async def add_fragment(self, sid: int, seq: int, idx: int, payload: bytes, offset: int):
        async with self._lock:
            stats = self._buffers[sid][seq]
            already_received = idx in stats.received
            if not already_received:
                stats.received[idx] = payload
                stats.count += 1
                stats.size += len(payload)
                stats.assembled[offset:offset + len(payload)] = payload
        # logging.debug(f"⚡️ FragmentBuffer.add_fragment({sid}, {seq}, {idx}, offset={offset}, len={len(payload)}) -> already_received={already_received}")
        return stats

    async def is_complete(self, sid: int, seq: int) -> bool:
        async with self._lock:
            stat = self._buffers[sid][seq]
            result = stat.count == stat.total and not stat.added_to_stats
        # logging.debug(f"⚡️ FragmentBuffer.is_complete({sid}, {seq}) -> {result}")
        return result

    async def all_arrived(self, sid: int, seq: int) -> bool:
        async with self._lock:
            stat = self._buffers[sid][seq]
            result = stat.count == stat.total
        # logging.debug(f"⚡️ FragmentBuffer.all_arrived({sid}, {seq}) -> {result}")
        return result

    async def is_ready(self, sid: int, seq: int) -> bool:
        async with self._lock:
            stat = self._buffers[sid][seq]
            result = stat.count == stat.total and not stat.added_to_stats
        # logging.debug(f"⚡️ FragmentBuffer.is_ready({sid}, {seq}) -> {result}")
        return result

    async def is_done(self, sid: int, seq: int) -> bool:
        async with self._lock:
            stat = self._buffers[sid][seq]
            result = stat.count == stat.total and stat.added_to_stats
        # logging.debug(f"⚡️ FragmentBuffer.is_done({sid}, {seq}) -> {result}")
        return result

    async def get(self, sid: int, seq: int) -> ConnectionStats:
        async with self._lock:
            result = self._buffers[sid][seq]
        # logging.debug(f"⚡️ FragmentBuffer.get({sid}, {seq}) -> found={result is not None}")
        return result

    async def set_done(self, sid: int, seq: int):
        async with self._lock:
            self._buffers[sid][seq].added_to_stats = True
        # logging.debug(f"⚡️ FragmentBuffer.set_done({sid}, {seq})")

    async def ready_sequences(self):
        # logging.debug(f"⚡️ FragmentBuffer.ready_sequences called")
        async with self._lock:
            for sid, seqs in self._buffers.items():
                for seq, stat in seqs.items():
                    if stat.count == stat.total and stat.added_to_stats:
                        # logging.debug(f"⚡️ FragmentBuffer.ready_sequences yielding sid={sid}, seq={seq}")
                        yield sid, seq, stat
                    else:
                        pass
                        # logging.error(f"⚡️ FragmentBuffer.ready_sequences sid={sid}, seq={seq} not done yet")

    async def all(self):
        async with self._lock:
            result = list(self._buffers.items())
        # logging.debug(f"⚡️ FragmentBuffer.all() -> total_senders={len(result)}")
        return result

    async def handle_fragment(self, reader, sid, header, arrival_time, stats, addr, writer):
        next_seq = await reader.get_next_seq()
        if header.seq < next_seq:
            await self.delete_seq(sid, header.seq)
            # logging.debug(f"⚡️ Skipping old seq {header.seq} < {next_seq}")
            return False

        stat = await self.get_or_create(sid, header.seq, header.total, header.timestamp)
        await self.add_fragment(sid, header.seq, header.idx, header.payload, header.idx * UdpConfig.MAX_UDP_PAYLOAD)

        if await self.is_ready(sid, header.seq):
            real_duration = arrival_time - stat.start_time
            stats.total_fragments(addr, header.total)
            stats.total_bytes(addr, stat.size)
            stats.total_sequences(addr, 1)
            stats.total_real_time(addr, real_duration)
            stats.rtt(addr, writer.get_rtt())
            stats.not_acked(addr, await writer.get_not_acked())
            await self.set_done(sid, header.seq)
            # logging.debug(f"⚡️ FragmentBuffer.handle_fragment marked sid={sid} seq={header.seq} as done")
            return True

        return False

