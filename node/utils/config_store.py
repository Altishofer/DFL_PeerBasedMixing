from dataclasses import dataclass, field
from typing import List

@dataclass
class ConfigStore:
    max_hops: int = 3
    resend_time: int = 60
    push_metric_interval: int = 1
    timeout_model_collection: int = 60
    batch_size: int = 64
    n_batches_per_round: int = 50
    dirichlet_alpha: float = 5.0
    port: int = 8000
    node_id: int = 0
    n_nodes: int = 5
    n_rounds: int = 3
    exit_nodes: List[int] = field(default_factory=lambda:[])
    join_nodes: List[int] = field(default_factory=lambda:[])
    mix_enabled: bool = True
    mix_mu: float = 0.005
    mix_std: float = 0.002
    mix_shuffle: bool = True
    mix_outbox_size: int = 10
    nr_cover_bytes: int = 100
    n_fragments_per_model: int = 200
    pause_training: bool = False
