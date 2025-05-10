import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import timedelta
from cachetools import TTLCache

from docker_utils import NodeService, MetricsService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

node_service = NodeService()
metrics_service = MetricsService()

status_cache = TTLCache(maxsize=1, ttl=5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(metrics_service.collect_resource_metrics())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/start/{count}")
def start(count: int):
    node_service.stop_nodes()
    node_service.delete_file()
    node_service.start_nodes(count)
    return {"status": "started", "nodes": count}


@app.websocket("/ws/logs/{container_name}")
async def container_logs(websocket: WebSocket, container_name: str):
    await metrics_service.stream_container_logs(websocket, container_name)


@app.post("/stop")
def stop():
    node_service.stop_nodes()
    node_service.delete_file()
    return {"status": "stopped"}


@app.get("/status")
async def status():
    if "status" in status_cache:
        return status_cache["status"]

    status_data = node_service.get_status()
    status_cache["status"] = status_data
    return status_data


@app.post("/report_metrics")
async def report_metrics(request: Request):
    return await metrics_service.receive_metrics(request)


@app.websocket("/ws/metrics")
async def metrics_websocket(websocket: WebSocket):
    await metrics_service.stream_metrics(websocket)


@app.get("/metrics")
async def get_all_metrics():
    return await metrics_service.get_all_metrics()
