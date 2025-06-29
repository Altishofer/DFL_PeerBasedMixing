from fastapi import APIRouter
from fastapi_cache.decorator import cache

from manager.services.node_service import node_service
from manager.models.schemas import NodeStatus
from manager.services.metrics_service import metrics_service

router = APIRouter(prefix="/nodes")

@router.post("/start")
async def start_nodes():
    await metrics_service.reset_file()
    await node_service.start_nodes()
    return {"status": "started"}

@router.post("/stop")
async def stop_nodes():
    await node_service.stop_nodes()
    return {"status": "stopped"}


@router.get("/status", response_model=list[NodeStatus])
@cache(expire=5)
async def get_status():
    return await node_service.get_status()