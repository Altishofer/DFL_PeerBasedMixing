import time
from dataclasses import dataclass
import hashlib
import struct


@dataclass
class PacketHeader:
    seq: int
    sid: int
    total: int
    idx: int
    timestamp: float
    digest: bytes
    payload: bytes

    @staticmethod
    def parse(data: bytes) -> "PacketHeader":
        if len(data) < 32:
            raise ValueError("Data too short to contain valid header")
        seq, sid, total, idx, ts = struct.unpack("!IIIId", data[:24])
        rdigest = data[-8:]
        payload = data[24:-8]
        edigest = hashlib.sha256(data[:24] + payload).digest()[:8]
        if edigest != rdigest:
            raise ValueError("Digest mismatch")
        return PacketHeader(seq, sid, total, idx, ts, rdigest, payload)

    @staticmethod
    def build(seq: int, sid: int, total: int, idx: int, payload: bytes, timestamp: float = None) -> bytes:
        if timestamp is None:
            timestamp = time.time()
        header = struct.pack("!IIIId", seq, sid, total, idx, timestamp)
        digest = hashlib.sha256(header + payload).digest()[:8]
        return header + payload + digest
