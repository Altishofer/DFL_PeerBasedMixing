import os
from pathlib import Path


class Settings:
    METRICS_DIR = Path("./metrics")
    METRICS_FILE = METRICS_DIR / "metrics.msgpack"
    IMAGE_NAME = "dfl_node"
    NETWORK_NAME = "dflnet"
    BASE_IP_PREFIX = "192.168.0"
    SUBNET = "192.168.0.0/24"
    GATEWAY = "192.168.0.254"
    METRICS_INTERVAL = 3
    FLUSH_INTERVAL = 1
    SECRETS_PATH = os.path.abspath("./secrets")
    NODE_PATH = os.path.abspath("./node")
    N_ROUNDS: int = 10
    N_NODES: int = 5
    MIX_ENABLED = False
    MIX_LAMBDA = 0.5
    MIX_MU = 0.2

    def __init__(self):
        self.METRICS_DIR.mkdir(exist_ok=True)


settings = Settings()