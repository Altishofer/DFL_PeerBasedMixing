from dataclasses import dataclass

@dataclass
class ConfigStore:
    max_hops: int = 2