from dataclasses import dataclass, field
from typing import List

@dataclass
class ConfigStore:
    max_hops: int = 2
    resend_time: int = 15
    push_metric_interval: int = 1
    timeout_model_collection: int = 60
    batch_size: int = 64
    n_batches_per_round: int = 10
    dirichlet_alpha: float = 10.0
    port: int = 8000
    node_id: int = 0
    n_nodes: int = 5
    n_rounds: int = 10
    exit_nodes: List[int] = field(default_factory=lambda: [0])
    join_nodes: List[int] = field(default_factory=lambda: [4])
    stream_mode: bool = False
    mix_enabled: bool = True
    mix_lambda: float = 0.001
    mix_shuffle: bool = True
    nr_cover_bytes: int = 100