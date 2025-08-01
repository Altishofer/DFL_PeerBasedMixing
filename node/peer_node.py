import asyncio

from communication.mixing import Mixer
from communication.sphinx.sphinx_transport import SphinxTransport
from learning.learner import Learner
from utils.config_store import ConfigStore


class PeerNode:
    def __init__(self, node_config: ConfigStore):
        self._node_id = node_config.node_id
        peers = {
            i: (f"node_{i}", node_config.port)
            for i in range(node_config.n_nodes)
        }


        self._transport = SphinxTransport(node_config.node_id, node_config.port, peers, node_config)
        self._learning = Learner(node_config, self._transport)

    async def start(self):
        await self._transport.start()
        await self._learning.run()
        # await asyncio.sleep(1000)
        await self._transport.close_all_connections()
        await asyncio.sleep(90)
