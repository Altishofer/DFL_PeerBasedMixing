import asyncio

from communication.sphinx.sphinx_transport import SphinxTransport
from learning.learner import Learner
from metrics.node_metrics import init_metrics


class PeerNode:
    def __init__(self, node_id, port, peers, host_name):
        self._node_id = node_id
        self._transport = SphinxTransport(node_id, port, peers)
        self._learning = Learner(node_id, self._transport, total_peers=len(peers))
        self._metrics = init_metrics(controller_url="http://host.docker.internal:8000", host_name=host_name)

    async def start(self):
        await self._transport.start()
        await self._learning.run()
        await asyncio.sleep(15)
