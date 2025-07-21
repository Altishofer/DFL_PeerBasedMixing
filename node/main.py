import asyncio
import logging
import os

from metrics.node_metrics import init_metrics, metrics
from peer_node import PeerNode
from utils.config_store import ConfigStore
from utils.logging_config import setup_logging


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

    if config.node_id in config.join_nodes:
        join_round = 5
        logging.info(f"Node waiting to join in round {join_round}")
        await metrics().wait_for_round(join_round)
    if config.node_id in config.exit_nodes:
        config.n_rounds = 5
        logging.info(f"Node exits after Round {config.n_rounds}")

    node = PeerNode(config)
    await node.start()


if __name__ == "__main__":
    asyncio.run(node_main())
