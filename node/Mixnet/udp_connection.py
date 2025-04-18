from dataclasses import dataclass

from nebula.core.network.udp_stack.udp_reader import UdpReader
from nebula.core.network.udp_stack.udp_writer import UdpWriter


@dataclass
class UdpConnection:
    reader: UdpReader
    writer: UdpWriter
