import asyncio
import datetime
import json
import os
import logging
import subprocess
from collections import deque
from contextlib import asynccontextmanager

import aiofiles
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.models import Response

from docker_utils import (
    collect_resource_metrics,
    append_metrics_to_file,
    start_nodes,
    stop_nodes,
    get_status
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

METRICS_DIR = "metrics"
os.makedirs(METRICS_DIR, exist_ok=True)
recent_metrics = deque(maxlen=10000)
websockets = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(collect_resource_metrics(recent_metrics))
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
    stop_nodes()
    filename = os.path.join(METRICS_DIR, "metrics.jsonl")
    if os.path.exists(filename):
        os.remove(filename)
    start_nodes(count)
    return {"status": "started", "nodes": count}

@app.websocket("/ws/logs/{container_name}")
async def container_logs(websocket: WebSocket, container_name: str):
    await websocket.accept()
    process = subprocess.Popen(
        ['docker', 'logs', '-f', container_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    try:
        while True:
            line = process.stdout.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue
            await websocket.send_text(line.strip())
    except WebSocketDisconnect:
        pass
    finally:
        process.kill()
        await websocket.close()


@app.post("/stop")
def stop():
    stop_nodes()
    return {"status": "stopped"}

@app.get("/status")
def status():
    return get_status()

@app.post("/receive_metrics")
async def receive_metrics(request: Request):
    try:
        metrics = await request.json()
        logging.info(f"/receive_metrics received {len(metrics)} entries")
        await append_metrics_to_file(metrics, recent_metrics)
        return {"status": "ok", "received": len(metrics)}
    except Exception as e:
        logging.error(f"/receive_metrics failed: {e}")
        return {"error": str(e)}

@app.websocket("/ws/metrics")
async def metrics_websocket(websocket: WebSocket):
    await websocket.accept()
    websockets.add(websocket)

    try:
        if recent_metrics:
            await websocket.send_text(json.dumps(list(recent_metrics)))
            recent_metrics.clear()

        while True:
            await asyncio.sleep(1)
            if recent_metrics:
                await websocket.send_text(json.dumps(list(recent_metrics)))
                recent_metrics.clear()
    except WebSocketDisconnect:
        websockets.discard(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        websockets.discard(websocket)


@app.get("/metrics")
async def get_all_metrics():
    filename = os.path.join(METRICS_DIR, "metrics.jsonl")
    if not os.path.exists(filename):
        return []

    metrics = []
    async with aiofiles.open(filename, "r") as f:
        async for line in f:
            metrics.append(json.loads(line.strip()))
    return metrics
