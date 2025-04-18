import asyncio
import struct
import logging

import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.basicConfig(level=logging.INFO) #, force=True)


def ip_to_bytes(ip_str):
    return bytes(int(part) for part in ip_str.split('.'))


def bytes_to_ip(ip_bytes):
    return '.'.join(str(b) for b in ip_bytes)


def pack_addr(addr):
    ip_bytes = ip_to_bytes(addr[0])
    port_bytes = struct.pack("!H", int(addr[1]))
    return ip_bytes + port_bytes


def unpack_addr(data):
    ip_bytes = data[0:4]
    port_bytes = data[4:6]
    ip = bytes_to_ip(ip_bytes)
    port = struct.unpack("!H", port_bytes)[0]
    # logging.debug(f"⚡️ MixNet.unpack_adr {ip}:{port}")
    return str(ip), int(port)


def onion_wrap(payload, route, original_ip, original_port):
    address_prefix = pack_addr(("0.0.0.0", 0))
    sender_address = pack_addr((original_ip, original_port))

    for hop in reversed(route[1:]):
        address_prefix = pack_addr(hop) + address_prefix

    output_payload = address_prefix + sender_address + payload
    return route[0], output_payload


def onion_peel(data):
    ip, port = unpack_addr(data)
    return (ip, port), data[6:]
