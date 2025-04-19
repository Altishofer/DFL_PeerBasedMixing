import os
import time
from peer_node import PeerNode
from logging_config import setup_logging
import logging

def load_env(key):
    env = os.environ.get(key)
    if env is None:
        raise ValueError(f"Env {key} is not set")
    return env

def node_main():
    node_id = int(load_env("NODE_ID"))
    n_nodes = int(load_env("N_NODES"))
    port = 5000 + node_id

    setup_logging(node_id)
    logging.info(f"Starting node on port {port}")

    peers = {
        i: (f"node_{i}", 5000 + i)
        for i in range(n_nodes)
    }

    logging.info(f"Peers: {peers}")

    node = PeerNode(node_id=node_id, port=port, peers=peers)
    node.start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    node_main()