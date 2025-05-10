from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from manager.services.node_service import node_service
from manager.models.schemas import StartRequest, NodeStatus
from manager.services.cache_service import cache_service

router = APIRouter(prefix="/nodes")

@router.post("/start")
async def start_nodes(request: StartRequest):
    await node_service.start_nodes(request.count)
    return {"status": "started", "nodes": request.count}

@router.post("/stop")
async def stop_nodes():
    await node_service.stop_nodes()
    return {"status": "stopped"}

@router.get("/status", response_model=list[NodeStatus])
async def get_status(use_cache: bool = True):
    if use_cache:
        cached = await cache_service.get_status()
        if cached:
            return cached
    return await node_service.get_status()