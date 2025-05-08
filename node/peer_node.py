import asyncio
import random

from communication.sphinx.sphinx_transport import SphinxTransport
from learning.learner import Learner


class PeerNode:
    def __init__(self, node_id, port, peers):
        self._node_id = node_id
        self._transport = SphinxTransport(node_id, port, peers)
        self._learning = Learner(node_id, self._transport, total_peers=len(peers))

    async def start(self):
        await self._transport.start()
        await self._learning.run()
        await asyncio.sleep(15)
