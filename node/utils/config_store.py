from dataclasses import dataclass, field
from typing import List


@dataclass
class ConfigStore:
    max_hops: int = 2
    resend_time: int = 40
    push_metric_interval: int = 1
    timeout_model_collection: int = 120
    batch_size: int = 64
    n_batches_per_round: int = 150  # training batches depends on nodes (total 10k samples with batch size of 64) 157 validation batches
    dirichlet_alpha: float = 10.0
    port: int = 8000
    node_id: int = 0
    n_nodes: int = 6
    n_rounds: int = 10
    exit_nodes: List[int] = field(default_factory=lambda: [])
    join_nodes: List[int] = field(default_factory=lambda: [])
    stream_mode: bool = False
    mix_enabled: bool = True
    mix_lambda: float = 0.001
    mix_shuffle: bool = True
    nr_cover_bytes: int = 100
