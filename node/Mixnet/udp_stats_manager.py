import tabulate

from nebula.core.network.udp_stack.udp_server_stats import ServerStats
import logging

class StatsManager:
    def __init__(self):
        self._stats = {}

    def get(self, addr):
        if addr not in self._stats:
            self._stats[addr] = ServerStats()
        return self._stats[addr]

    def all(self):
        return self._stats.items()

    def reset(self, addr=None):
        if addr:
            self._stats[addr] = ServerStats()
        else:
            self._stats.clear()

    def forwarded_message(self, addr):
        self.get(addr).mix_forward += 1


    def lost_fragments(self, addr, n_fragments):
        self.get(addr).lost_fragments += n_fragments

    def ack_messages(self, addr, n_acks):
        self.get(addr).ack_messages += n_acks

    def total_fragments(self, addr, value):
        self.get(addr).total_fragments += value

    def total_bytes(self, addr, size):
        self.get(addr).total_bytes += size

    def total_sequences(self, addr, value):
        self.get(addr).total_sequences += value

    def total_real_time(self, addr, value):
        self.get(addr).total_real_time += value

    def rtt(self, addr, value):
        self.get(addr).rtt = value

    def not_acked(self, addr, value):
        self.get(addr).not_acked = value

    def print_stats(self):
        # logging.debug("⚡️ UdpServer.log_statistics called")
        rows = []
        for addr, stat in self.all():
            if stat.total_real_time > 0:
                overall_tx_mbps = (stat.total_bytes * 8) / stat.total_real_time / 1_000_000
            else:
                overall_tx_mbps = 0

            if stat.total_real_time > 0:
                overall_seq_time = stat.total_real_time / stat.total_sequences
            else:
                overall_seq_time = 0

            lost_percent = 0
            if stat.total_fragments > 0:
                lost_percent = (stat.lost_fragments / stat.total_fragments) * 100

            rows.append([
                f"{addr[0]}:{addr[1]}",
                stat.total_sequences,
                stat.total_fragments,
                f"{stat.total_bytes/1e6:.2f}",
                f"{overall_tx_mbps:.2f}",
                stat.lost_fragments,
                f"{lost_percent:.2f}",
                stat.ack_messages,
                f"{stat.rtt:.2f}",
                stat.not_acked,
                f"{overall_seq_time:.2f}",
                stat.mix_forward,
            ])
        headers = [
            "Client",
            "Seq",
            "Frags",
            "Recv(MB)",
            "AvgDataRate (Mbps)",
            "LostFrags",
            "LostFrags (%)",
            "SentACK",
            "RTT",
            "NotAck",
            "t/seq (sec)",
            "Mixed",
        ]
        sorted_rows = sorted(rows, key=lambda x: int(x[0].split(":")[1]))
        logging.info(
            "\n" +
            tabulate.tabulate(sorted_rows, headers=headers, tablefmt="grid")
            + "\n"
        )

    def all_addresses(self):
        return self._stats.keys()

