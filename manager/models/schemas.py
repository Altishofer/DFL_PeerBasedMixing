from dataclasses import dataclass

from pydantic import BaseModel

class NodeStatus(BaseModel):
    name: str
    status: str
    started_at: str

class MetricPoint(BaseModel):
    timestamp: str
    field: str
    value: float | str
    node: str

@dataclass
class NodeConfig:
    n_nodes: int = 5
    n_rounds: int = 10
