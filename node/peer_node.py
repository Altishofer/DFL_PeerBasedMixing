import asyncio

from communication.sphinx.sphinx_transport import SphinxTransport
from learning.learner import Learner
from metrics.node_metrics import init_metrics
from models.schemas import NodeConfig


class PeerNode:
    def __init__(self, node_config : NodeConfig, host_name):
        self._node_id = node_config.node_id
        peers = {
            i: (f"node_{i}", node_config.port)
            for i in range(node_config.n_nodes)
        }
        self._metrics = init_metrics(controller_url="http://host.docker.internal:8000", host_name=host_name)
        self._transport = SphinxTransport(node_config.node_id, node_config.port, peers)
        self._learning = Learner(node_config, self._transport)

    async def start(self):
        await self._transport.start()
        await self._learning.run()
        await asyncio.sleep(15)
