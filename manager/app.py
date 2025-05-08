import os

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

        timestamp = datetime.utcnow().strftime("%Y%m%d")
        filename = os.path.join(METRICS_DIR, f"metrics_{timestamp}.jsonl")

        async with aiofiles.open(filename, "a") as f:
            for entry in metrics:
                line = json.dumps(entry, separators=(",", ":"))
                await f.write(line + "\n")

        return {"status": "ok", "received": len(metrics)}
    except Exception as e:
        return {"error": str(e)}