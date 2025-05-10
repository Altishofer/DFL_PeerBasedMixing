import asyncio
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
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
                metrics_dict = [metric.dict() for metric in metrics]
                await websocket.send_json(metrics_dict)
                await cache_service.clear_metrics()
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

@router.post("/push", response_model=List[MetricPoint])
async def push_metrics(new_metrics: List[MetricPoint]):
    try:
        await cache_service.add_metrics(new_metrics)
        await metrics_service._store_metrics(new_metrics)
        return new_metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to store metrics")