import datetime
import json
import os

import aiofiles
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from docker_utils import start_nodes, stop_nodes, get_status

METRICS_DIR = "metrics"
os.makedirs(METRICS_DIR, exist_ok=True)
app = FastAPI()

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
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    filename = os.path.join(METRICS_DIR, f"metrics_{timestamp}.jsonl")
    if os.path.exists(filename):
        os.remove(filename)
    start_nodes(count)
    return {"status": "started", "nodes": count}


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
        if not isinstance(metrics, list):
            return {"error": "Expected a list of metrics"}

        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
        filename = os.path.join(METRICS_DIR, f"metrics_{timestamp}.jsonl")

        async with aiofiles.open(filename, "a") as f:
            for entry in metrics:
                await f.write(json.dumps(entry, separators=(",", ":")) + "\n")

        return {"status": "ok", "received": len(metrics)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics")
async def get_metrics():
    try:
        filename = os.path.join(
            METRICS_DIR,
            f"metrics_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}.jsonl"
        )
        if not os.path.exists(filename):
            return []

        metrics = []
        async with aiofiles.open(filename, "r") as f:
            async for line in f:
                try:
                    metrics.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        return metrics
    except Exception as e:
        return {"error": str(e)}