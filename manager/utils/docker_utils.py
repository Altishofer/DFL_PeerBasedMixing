import os
import pickle
import docker
from sphinxmix.SphinxParams import SphinxParams
from manager.config import settings

_client = None

def get_docker_client():
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client

def generate_keys(n: int):
    params = SphinxParams()
    group = params.group
    pkiPriv_raw = {}
    pkiPub_raw = {}

    for nid in range(n):
        x = group.gensecret()
        y = group.expon(group.g, [x])
        pkiPriv_raw[nid] = (nid, x.binary(), y.export())
        pkiPub_raw[nid] = (nid, y.export())

    os.makedirs("./secrets", exist_ok=True)
    with open("./secrets/pki_priv.pkl", "wb") as f:
        pickle.dump(pkiPriv_raw, f)
    with open("./secrets/pki_pub.pkl", "wb") as f:
        pickle.dump(pkiPub_raw, f)

def create_network():
    client = get_docker_client()
    try:
        client.networks.get(settings.NETWORK_NAME)
    except docker.errors.NotFound:
        ipam_pool = docker.types.IPAMPool(
            subnet=settings.SUBNET,
            gateway=settings.GATEWAY
        )
        ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
        client.networks.create(
            settings.NETWORK_NAME,
            driver="bridge",
            ipam=ipam_config
        )

def stop_all_nodes():
    client = get_docker_client()
    containers = client.containers.list(all=True)
    for c in containers:
        if c.name.startswith("node_"):
            try:
                if c.status == "running":
                    c.stop(timeout=5)
                c.remove(force=True)
            except docker.errors.APIError:
                continue