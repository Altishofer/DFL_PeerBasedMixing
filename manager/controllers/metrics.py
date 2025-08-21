import asyncio
import json
import logging
from typing import List, Set

from fastapi import APIRouter, WebSocket, HTTPException
from fastapi import Request
from sse_starlette import EventSourceResponse

from manager.models.schemas import MetricPoint
from manager.services.cache_service import cache_service
from manager.services.metrics_service import metrics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics")


@router.on_event("startup")
async def start_background_broadcast():
    asyncio.create_task(broadcast_loop())


active_connections: Set[WebSocket] = set()
broadcast_lock = asyncio.Lock()


@router.get("/sse")
async def metrics_sse(request: Request):
    async def event_generator():
        all_metrics = await metrics_service.get_all_metrics()
        if all_metrics:
            yield {"data": json.dumps([m.model_dump() for m in all_metrics])}
        while True:
            if await request.is_disconnected():
                break
            latest_cache = await cache_service.pop_all_metrics()
            if latest_cache:
                data = [m.model_dump() for m in latest_cache]
                yield {"data": json.dumps(data)}
            await asyncio.sleep(0.0001)

    return EventSourceResponse(event_generator())


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


@router.get("/clear")
async def clear_metrics():
    try:
        await metrics_service.save_to_csv()
        await cache_service.clear_cache()
        return {"status": "success", "message": "Metrics cleared"}
    except Exception as e:
        logger.error(f"Failed to clear metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear metrics")


@router.post("/push", response_model=List[MetricPoint])
async def push_metrics(new_metrics: List[MetricPoint]):
    try:
        await cache_service.add_metrics(new_metrics)
        await metrics_service.enqueue_metrics(new_metrics)
        return new_metrics
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to store metrics")
