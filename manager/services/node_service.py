import asyncio
import json
from typing import List
from manager.config import settings
from manager.models.schemas import NodeStatus, StartRequest
from node.models.schemas import NodeConfig
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

    async def start_nodes(self, start_request: StartRequest) -> None:
        await asyncio.to_thread(self._start_nodes_sync, start_request)

    def _start_nodes_sync(self, start_request: StartRequest) -> None:
        stop_all_nodes()
        create_network()
        generate_keys(start_request.nodeCount)

        for i in range(start_request.nodeCount):
            name = f"node_{i}"

            data = start_request.model_dump()
            data["n_nodes"] = data.pop("nodeCount")
            data.update({
                "node_id": i, 
                "port": 8000,
                "exit": i == 0,
                "join": i == start_request.nodeCount -1
            })

            node_config = NodeConfig(**data)

            # handle nested data structure
            env_vars = {
                str(k).upper(): json.dumps(v) if isinstance(v, dict) else str(v)
                for k, v in node_config.model_dump().items()
            }

            self._client.containers.run(
                settings.IMAGE_NAME,
                name=name,
                environment=env_vars,
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
