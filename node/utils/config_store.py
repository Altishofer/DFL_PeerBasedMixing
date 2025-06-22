from dataclasses import dataclass


@dataclass
class ConfigStore:
    max_hops: int = 2
    resend_time: int = 10
    push_metric_interval: int = 3
    timeout_model_collection: int = 20
