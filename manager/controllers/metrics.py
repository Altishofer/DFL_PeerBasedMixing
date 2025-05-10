import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from manager.services.metrics_service import metrics_service
from manager.services.cache_service import cache_service
from manager.models.schemas import MetricPoint

router = APIRouter(prefix="/metrics")


@router.get("", response_model=list[MetricPoint])
async def get_metrics():
    return await metrics_service.get_all_metrics()


@router.websocket("/ws")
async def metrics_websocket(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            metrics = await cache_service.get_metrics()
            if metrics:
                await websocket.send_json(metrics)
                await cache_service.clear_metrics()
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass