from dataclasses import dataclass


@dataclass
class ConfigStore:
    max_hops: int = 2
    resend_time: int = 2
    push_metric_interval: int = 1
    timeout_model_collection: int = 30
    batch_size: int = 64
    n_batches_per_round: int = 10
    dirichlet_alpha: float = 10.0
    bytes_per_chunk = 600
