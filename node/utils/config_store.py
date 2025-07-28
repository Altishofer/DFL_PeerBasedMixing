from dataclasses import dataclass, field
from typing import List


@dataclass
class ConfigStore:
    max_hops: int = 2
    resend_time: int = 60
    push_metric_interval: int = 1
    timeout_model_collection: int = 120
    batch_size: int = 64
    n_batches_per_round: int = 2000  # train batches depend on n of nodes, min of param or available batches is taken
    dirichlet_alpha: float = 10.0
    port: int = 8000
    node_id: int = 0
    n_nodes: int = 6
    n_rounds: int = 10
    exit_nodes: List[int] = field(default_factory=lambda:[0])
    join_nodes: List[int] = field(default_factory=lambda:[])
    mix_enabled: bool = True
    mix_mu: float = 0.005
    mix_std: float = 0.001
    mix_shuffle: bool = True
    mix_outbox_size: int = 10
    nr_cover_bytes: int = 100
    pause_training: bool = False
    cache_covers: bool = False
