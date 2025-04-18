import docker

client = docker.from_env()
IMAGE = "dfl_node"
NETWORK = "dflnet"

def create_network():
    try:
        client.networks.get(NETWORK)
    except docker.errors.NotFound:
        client.networks.create(NETWORK)

def start_nodes(n):
    create_network()
    for i in range(n):
        client.containers.run(
            IMAGE,
            name=f"node{i}",
            environment={"NODE_ID": str(i), "NUM_NODES": str(n)},
            detach=True,
            network=NETWORK
        )

def stop_nodes():
    for c in client.containers.list(all=True):
        if c.name.startswith("node"):
            c.stop()
            c.remove()

def get_status():
    return [
        {"name": c.name, "status": c.status}
        for c in client.containers.list(all=True)
        if c.name.startswith("node")
    ]