from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from docker_utils import start_nodes, stop_nodes, get_status

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