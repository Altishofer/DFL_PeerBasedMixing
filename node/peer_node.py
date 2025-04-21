import asyncio
import random

from sphinx_transport import SphinxTransport
from learning import Learning


class PeerNode:
    def __init__(self, node_id, port, peers):
        self._node_id = node_id
        self._transport = SphinxTransport(node_id, port, peers)
        self._learning = Learning(node_id, self._transport, total_peers=len(peers))

    async def start(self):
        await self._transport.start()
        await asyncio.sleep(1)
        await self._learning.run()
