import asyncio
import datetime
import json
import os
import logging
import pickle
import subprocess
import uuid
from collections import deque
import aiofiles
import docker
from sphinxmix.SphinxParams import SphinxParams
from fastapi import WebSocket, Request, WebSocketDisconnect


client = docker.from_env()
IMAGE = "dfl_node"
NETWORK = "dflnet"
BASE_IP_PREFIX = "192.168.0"
SUBNET = "192.168.0.0/24"
GATEWAY = "192.168.0.254"
METRICS_DIR = "metrics"
os.makedirs(METRICS_DIR, exist_ok=True)

recent_metrics = deque(maxlen=100000)

class NodeService:
    def start_nodes(self, n):
        self.stop_nodes()
        self.create_network()
        self.generate_keys(n)

        for i in range(n):
            name = f"node_{i}"
            ip = f"{BASE_IP_PREFIX}{i}"
            client.containers.run(
                IMAGE,
                name=name,
                environment={
                    "NODE_ID": str(i),
                    "N_NODES": str(n),
                    "PORT": str(5000)
                },
                volumes={
                    os.path.abspath("../secrets"): {
                        "bind": "/config/",
                        "mode": "ro"
                    },
                    os.path.abspath("../node"): {
                        "bind": "/node",
                        "mode": "ro"
                    }
                },
                detach=True,
                network=NETWORK,
                hostname=f"node_{i}",
                init=True,
                extra_hosts={"host.docker.internal": "host-gateway"}
            )

    def stop_nodes(self):
        containers = client.containers.list(all=True)
        for c in containers:
            try:
                if c.name.startswith("node_"):
                    if c.status == "running":
                        c.stop(timeout=5)
                    c.remove(force=True)
            except docker.errors.APIError as e:
                print(f"[!] Failed to stop/remove {c.name}: {e}")

    def get_status(self):
        containers = client.containers.list(all=False)
        return [
            {
                "name": c.name,
                "status": c.status,
                "started_at": c.attrs["State"]["StartedAt"]
            }
            for c in containers
            if c.name.startswith("node")
        ]

    def create_network(self):
        try:
            client.networks.get(NETWORK)
        except docker.errors.NotFound:
            ipam_pool = docker.types.IPAMPool(subnet=SUBNET, gateway=GATEWAY)
            ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
            client.networks.create(NETWORK, driver="bridge", ipam=ipam_config)

    def generate_keys(self, n):
        params = SphinxParams()
        group = params.group
        node_ids = range(n)
        pkiPriv_raw = {}
        pkiPub_raw = {}

        for nid in node_ids:
            x = group.gensecret()
            y = group.expon(group.g, [x])
            pkiPriv_raw[nid] = (nid, x.binary(), y.export())
            pkiPub_raw[nid] = (nid, y.export())

        with open("../secrets/pki_priv.pkl", "wb") as f:
            pickle.dump(pkiPriv_raw, f)

        with open("../secrets/pki_pub.pkl", "wb") as f:
            pickle.dump(pkiPub_raw, f)

    def delete_file(self):
        filename = os.path.join(METRICS_DIR, "metrics.jsonl")
        if os.path.exists(filename):
            os.remove(filename)

class MetricsService:
    async def receive_metrics(self, request: Request):
        try:
            metrics = await request.json()
            await self.append_metrics_to_file(metrics)
            return {"status": "ok", "received": len(metrics)}
        except Exception as e:
            return {"error": str(e)}

    async def append_metrics_to_file(self, metrics):
        if not metrics:
            return

        filename = os.path.join(METRICS_DIR, f"metrics.jsonl")
        async with aiofiles.open(filename, "a") as f:
            for entry in metrics:
                entry["id"] = str(uuid.uuid1())
                recent_metrics.append(entry)
                await f.write(json.dumps(entry, separators=(",", ":")) + "\n")

    async def stream_container_logs(self, websocket: WebSocket, container_name: str):
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

    async def stream_metrics(self, websocket: WebSocket):
        await websocket.accept()
        try:
            if recent_metrics:
                await websocket.send_text(json.dumps(list(recent_metrics)))
                recent_metrics.clear()

            while True:
                await asyncio.sleep(3)
                if recent_metrics:
                    await websocket.send_text(json.dumps(list(recent_metrics)))
                    recent_metrics.clear()
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logging.error(f"WebSocket error: {e}")

    async def get_all_metrics(self):
        filename = os.path.join(METRICS_DIR, "metrics.jsonl")
        if not os.path.exists(filename):
            logging.error(f"Metrics file {filename} not found")
            return []

        metrics = []
        async with aiofiles.open(filename, "r") as f:
            async for line in f:
                metrics.append(json.loads(line.strip()))
        return metrics

    async def collect_resource_metrics(self):
        while True:
            containers = client.containers.list()
            active_nodes = [c for c in containers if c.name.startswith("node_")]

            if not active_nodes:
                await asyncio.sleep(3)
                continue

            timestamp_now = datetime.datetime.utcnow().isoformat() + "Z"
            lines = []

            for c in active_nodes:
                try:
                    stats = c.stats(stream=False)

                    cpu_total_ns = stats["cpu_stats"]["cpu_usage"]["total_usage"] / 10e9
                    memory_usage = stats["memory_stats"]["usage"]

                    node = c.name

                    lines.append({
                        "timestamp": timestamp_now,
                        "field": "cpu_total_ns",
                        "value": cpu_total_ns,
                        "node": node
                    })
                    lines.append({
                        "timestamp": timestamp_now,
                        "field": "memory_mb",
                        "value": round(memory_usage / (1024 * 1024), 2),
                        "node": node
                    })

                except Exception as e:
                    print(f"[metrics] Error reading stats for {c.name}: {e}")
                    continue

            if lines:
                recent_metrics.extend(lines)
                await self.append_metrics_to_file(lines)

            await asyncio.sleep(3)
