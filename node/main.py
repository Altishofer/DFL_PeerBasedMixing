from peer_node import PeerNode
import logging

import os
import asyncio
from utils.logging_config import setup_logging

def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"💥 Unhandled exception: {msg}")


def load_env(key):
    env = os.environ.get(key)
    if env is None:
        raise ValueError(f"Env {key} is not set")
    return env


async def node_main():
    node_id = int(load_env("NODE_ID"))
    n_nodes = int(load_env("N_NODES"))
    port = int(load_env("PORT"))

    setup_logging(node_id)

    peers = {
        i: (f"node_{i}", port)
        for i in range(n_nodes)
    }

    node = PeerNode(
        node_id=node_id,
        port=port,
        peers=peers,
        host_name=f"node_{node_id}"
    )
    await node.start()


if __name__ == "__main__":
    asyncio.run(node_main())
