import threading
import socket
import random
import time
import pickle
import logging

from petlib.bn import Bn
from petlib.ec import EcGroup, EcPt

from sphinxmix.SphinxParams import SphinxParams
from sphinxmix.SphinxClient import (
    create_forward_message, PFdecode, Relay_flag, Dest_flag,
    receive_forward, Nenc, pki_entry, pack_message, unpack_message
)
from sphinxmix.SphinxNode import sphinx_process

class PeerNode:
    def __init__(self, node_id, port, peers):
        self.node_id = node_id
        self.port = port
        self.peers = peers
        self.params = SphinxParams()
        self.group = self.params.group
        self.pkiPriv = dict()
        self.pkiPub = dict()
        self.load_keys()

    def load_keys(self):

        priv_path = "/config/pki_priv.pkl"
        pub_path = "/config/pki_pub.pkl"

        with open(priv_path, "rb") as f:
            priv_raw = pickle.load(f)

        with open(pub_path, "rb") as f:
            pub_raw = pickle.load(f)

        ec = EcGroup()
        self.pkiPriv = {}
        self.pkiPub = {}

        for nid, x_bytes, y_bytes in priv_raw.values():
            x = Bn.from_binary(x_bytes)
            y = EcPt.from_binary(y_bytes, ec)
            self.pkiPriv[nid] = pki_entry(nid, x, y)

        for nid, y_bytes in pub_raw.values():
            y = EcPt.from_binary(y_bytes, ec)
            self.pkiPub[nid] = pki_entry(nid, None, y)


    def start(self):
        threading.Thread(target=self.server_loop, daemon=True).start()
        time.sleep(1)
        self.send_loop()

    def server_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind(("0.0.0.0", self.port))
            server.listen()
            logging.info(f"[Node {self.node_id}] Listening on port {self.port}")
            while True:
                conn, _ = server.accept()
                threading.Thread(target=self.handle_connection, args=(conn,), daemon=True).start()

    def handle_connection(self, conn):
        with conn:
            try:
                data = conn.recv(65536)
                param_dict = {(self.params.max_len, self.params.m): self.params}
                _, (header, delta) = unpack_message(param_dict, data)
                x = self.pkiPriv[self.node_id].x
                tag, info, (header, delta), mac_key = sphinx_process(self.params, x, header, delta)
                routing = PFdecode(self.params, info)

                if routing[0] == Relay_flag:
                    _, next_id = routing
                    host, port = self.peers[next_id]
                    logging.info(f"[Node {self.node_id}] Relaying to Node {next_id}")
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.connect((host, port))
                        msg_bytes = pack_message(self.params, (header, delta))
                        sock.sendall(msg_bytes)

                elif routing[0] == Dest_flag:
                    dest, msg = receive_forward(self.params, mac_key, delta)
                    logging.info(f"[Node {self.node_id}] Received message for {dest.decode()}: {msg.decode()}")

            except Exception as e:
                logging.info(f"[Node {self.node_id}] Error handling connection: {e}")

    def send_loop(self):
        while True:
            time.sleep(random.randint(3, 6))
            self.send_random_message()

    def send_random_message(self):
        path = [nid for nid in self.peers if nid != self.node_id]
        random.shuffle(path)
        path = [self.node_id] + path
        nodes_routing = list(map(Nenc, path))
        keys_nodes = [self.pkiPub[n].y for n in path]
        dest = b"peer-message"
        message = f"Hi from node {self.node_id}".encode()
        header, delta = create_forward_message(self.params, nodes_routing, keys_nodes, dest, message)
        first_hop = path[0]
        host, port = self.peers[first_hop]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, port))
                msg_bytes = pack_message(self.params, (header, delta))
                sock.sendall(msg_bytes)
            logging.info(f"[Node {self.node_id}] Sent message to path {path}")
        except Exception as e:
            logging.info(f"[Node {self.node_id}] Failed to send message: {e}")