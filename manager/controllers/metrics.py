import asyncio
import logging
import time
from typing import List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from manager.services.metrics_service import metrics_service
from manager.models.schemas import MetricPoint
from manager.services.cache_service import cache_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics")

@router.on_event("startup")
async def start_background_broadcast():
    asyncio.create_task(broadcast_loop())

active_connections: Set[WebSocket] = set()
broadcast_lock = asyncio.Lock()


@router.websocket("/ws")
async def metrics_websocket(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        all_metrics = await metrics_service.get_all_metrics()
        await websocket.send_json(all_metrics)
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast_loop():
    while True:
        latest_cache = await cache_service.pop_all_metrics()
        if latest_cache:
            data = [m.model_dump() for m in latest_cache]

            async with broadcast_lock:
                disconnected = []
                send_tasks = []
                for ws in list(active_connections):
                    send_tasks.append(asyncio.create_task(ws.send_json(data)))
                results = await asyncio.gather(*send_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception) and i < len(active_connections):
                        disconnected_ws = list(active_connections)[i]
                        active_connections.remove(disconnected_ws)

                for ws in disconnected:
                    active_connections.remove(ws)
        await asyncio.sleep(1)

@router.post("/push", response_model=List[MetricPoint])
async def push_metrics(new_metrics: List[MetricPoint]):
    try:
        await cache_service.add_metrics(new_metrics)
        await metrics_service.enqueue_metrics(new_metrics)
        return new_metrics
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to store metrics")

