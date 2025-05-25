from pydantic import BaseModel

class NodeConfig(BaseModel):
    node_id: int
    rounds: int
    n_nodes: int
    stream: bool
    port: int
    join: bool
    exit: bool