from pydantic import BaseModel
from typing import List, Dict, Any

class NodeStatus(BaseModel):
    name: str
    status: str
    started_at: str

class MetricPoint(BaseModel):
    timestamp: str
    field: str
    value: float
    node: str

class StartRequest(BaseModel):
    count: int
    rounds: int
    stream: bool
    exitNodes: int
    joinNodes: int
    mixing_params: dict