import asyncio
import os
from typing import List
from manager.config import settings
from manager.models.schemas import NodeStatus
from manager.config import Settings
from manager.utils.docker_utils import (
    get_docker_client,
    create_network,
    generate_keys,
    stop_all_nodes
)

class NodeService:
    def __init__(self):
        self._client = get_docker_client()

    async def start_nodes(self, count: int) -> None:
        await asyncio.to_thread(self._start_nodes_sync, count)

    def _start_nodes_sync(self, count: int) -> None:
        stop_all_nodes()
        create_network()
        generate_keys(count)

        for i in range(count):
            name = f"node_{i}"

            self._client.containers.run(
                settings.IMAGE_NAME,
                name=name,
                environment={
                    "NODE_ID": str(i),
                    "N_NODES": str(count),
                    "PORT": "5000"
                },
                volumes={
                    Settings.SECRETS_PATH: {"bind": "/config/", "mode": "ro"},
                    Settings.NODE_PATH: {"bind": "/node", "mode": "ro"}
                },
                detach=True,
                network=settings.NETWORK_NAME,
                hostname=name,
                init=True,
                extra_hosts={"host.docker.internal": "host-gateway"}
            )

    async def stop_nodes(self) -> None:
        await asyncio.to_thread(stop_all_nodes)

    async def get_status(self) -> List[NodeStatus]:
        containers = await asyncio.to_thread(
            lambda: self._client.containers.list(all=True)
        )

        status = []
        active_node_names = set()

        for c in containers:
            if c.name.startswith("node_"):
                active_node_names.add(c.name)
                status.append(NodeStatus(
                    name=c.name,
                    status=c.status,
                    started_at=c.attrs["State"]["StartedAt"]
                ))

        return status

node_service = NodeService()
