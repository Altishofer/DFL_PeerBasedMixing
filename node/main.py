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
        node_id=int(load_env("NODE_ID"))
    )

    setup_logging(config.node_id)

    init_metrics(controller_url="http://host.docker.internal:8000", host_name=f"node_{config.node_id}")

    node = PeerNode(config)
    await node.start()

if __name__ == "__main__":
    asyncio.run(node_main())
