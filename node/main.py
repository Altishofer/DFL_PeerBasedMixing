import os
import time
import random

node_id = int(os.getenv("NODE_ID", 0))
num_nodes = int(os.getenv("NUM_NODES", 1))

def run():
    peers = [f"node{j}" for j in range(num_nodes) if j != node_id]
    while True:
        print(f"[Node {node_id}] Training... communicating with {random.choice(peers)}")
        time.sleep(random.uniform(1.0, 2.0))

if __name__ == "__main__":
    run()