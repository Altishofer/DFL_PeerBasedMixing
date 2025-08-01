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
    SECRETS_PATH = os.path.abspath("./secrets")
    NODE_PATH = os.path.abspath("./node")

    def __init__(self):
        self.METRICS_DIR.mkdir(exist_ok=True)


settings = Settings()