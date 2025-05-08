import os

import docker
import pickle
from sphinxmix.SphinxParams import SphinxParams


client = docker.from_env()
IMAGE = "dfl_node"
NETWORK = "dflnet"
BASE_IP_PREFIX = "192.168.0"
SUBNET = "192.168.0.0/24"
GATEWAY = "192.168.0.254"


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
    return [
        {"name": c.name, "status": c.status}
        for c in client.containers.list(all=True)
        if c.name.startswith("node")
    ]