from peer_node import PeerNode
import logging
import json
import os
import asyncio
from utils.config_store import ConfigStore
from utils.logging_config import setup_logging
from metrics.node_metrics import init_metrics


def load_env(key):
    env = os.environ.get(key)
    if env is None:
        raise ValueError(f"Env {key} is not set")
    return env


async def node_main():

    config = ConfigStore(
        node_id=int(load_env("NODE_ID")),
        n_nodes=int(load_env("N_NODES")),
        n_rounds=int(load_env("N_ROUNDS")),
    )

    setup_logging(config.node_id)

    init_metrics(controller_url="http://host.docker.internal:8000", host_name=f"node_{config.node_id}")

    # if config.node_id in config.join_nodes:
    #     logging.info(f"Node is waiting 1 min before joining.")
    #     await asyncio.sleep(60)
    # if config.node_id in config.exit_nodes:
    #     config.n_rounds = 3
    #     logging.info(f"Node will exit after Round {config.n_rounds}")

    node = PeerNode(config)
    await node.start()

if __name__ == "__main__":
    asyncio.run(node_main())
