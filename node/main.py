import time

from peer_node import PeerNode
import logging

import os
import asyncio
from utils.logging_config import setup_logging
from models.schemas import NodeConfig

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
    stream = load_env("STREAM") == "True"
    rounds = int(load_env("ROUNDS"))
    exit = bool(load_env("EXIT") == "True")
    join = bool(load_env("JOIN") == "True")

    setup_logging(node_id)

    node_config = NodeConfig(
        node_id=node_id,
        n_nodes=n_nodes,
        port=port,
        stream=stream,
        rounds=rounds,
        exit=exit,
        join=join
    )

    # if join:
    #     logging.info(f"Node is waiting 3 min before joining.")
    #     time.sleep(60)
    if exit:
        node_config.rounds = 0
        logging.info(f"Node will exit after Round {node_config.rounds}")

    node = PeerNode(
        node_config=node_config,
        host_name=f"node_{node_id}",
    )
    await node.start()

if __name__ == "__main__":
    asyncio.run(node_main())
