import os
import docker
import pickle
import asyncio
import datetime
import json
import aiofiles
from sphinxmix.SphinxParams import SphinxParams

client = docker.from_env()
IMAGE = "dfl_node"
NETWORK = "dflnet"
BASE_IP_PREFIX = "192.168.0"
SUBNET = "192.168.0.0/24"
GATEWAY = "192.168.0.254"
METRICS_DIR = "metrics"
os.makedirs(METRICS_DIR, exist_ok=True)

def generate_keys(n):
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

def create_network():
    try:
        client.networks.get(NETWORK)
    except docker.errors.NotFound:
        ipam_pool = docker.types.IPAMPool(subnet=SUBNET, gateway=GATEWAY)
        ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
        client.networks.create(NETWORK, driver="bridge", ipam=ipam_config)

def start_nodes(n):
    stop_nodes()
    create_network()
    generate_keys(n)

    for i in range(n):
        name = f"node_{i}"
        ip = f"{BASE_IP_PREFIX}{i}"
        print(f"Starting {name} @ {ip}")
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

def stop_nodes():
    containers = client.containers.list(all=True)
    for c in containers:
        try:
            if c.name.startswith("node_"):
                print(f"Stopping {c.name} (status: {c.status})")
                if c.status == "running":
                    c.stop(timeout=5)
                c.remove(force=True)
                print(f"Removed {c.name}")
        except docker.errors.APIError as e:
            print(f"[!] Failed to stop/remove {c.name}: {e}")

def get_status():
    containers = client.containers.list(all=True)
    return [
        {
            "name": c.name,
            "status": c.status,
            "started_at": c.attrs["State"]["StartedAt"]
        }
        for c in containers
        if c.name.startswith("node")
    ]

async def collect_resource_metrics():
    while True:
        containers = client.containers.list()
        active_nodes = [c for c in containers if c.name.startswith("node_")]

        if not active_nodes:
            await asyncio.sleep(1)
            continue

        timestamp_day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
        filename = os.path.join(METRICS_DIR, f"metrics_{timestamp_day}.jsonl")
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
            print(f"[metrics] Writing {len(lines)} entries to {filename}")
            async with aiofiles.open(filename, "a") as f:
                for entry in lines:
                    await f.write(json.dumps(entry, separators=(",", ":")) + "\n")

        await asyncio.sleep(1)
