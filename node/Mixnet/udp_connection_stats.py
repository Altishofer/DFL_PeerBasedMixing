import logging
from nebula.core.network.udp_stack.udp_config import UdpConfig


class ConnectionStats:

    def __init__(self, total: int, start_time: float):
        self.total = total
        self.count = 0
        self.size = 0
        self.start_time = start_time
        self.max_link_speed = 0
        self.received = dict()
        self.assembled = bytearray(total * UdpConfig.MAX_UDP_PAYLOAD)
        self.added_to_stats = False

    def print(self):
        logging.debug(
            f"⚡️ ConnectionStats: total={self.total}, "
            f"count={self.count}, "
            f"size={self.size}, "
            f"start_time={self.start_time:.3f}, "
            f"added_to_stats={self.added_to_stats}, "
            f"received={sorted(self.received.keys())}"
        )
