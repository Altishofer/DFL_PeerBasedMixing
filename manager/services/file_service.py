import msgpack
from typing import List
from manager.models.schemas import MetricPoint
from manager.config import settings

class FileService:
    def write(self, metrics: List[MetricPoint]):
        flat_metrics = [m.model_dump() for m in metrics]
        serialized = msgpack.packb(flat_metrics)
        with open(settings.METRICS_FILE, "ab") as f:
            f.write(serialized)

    def reset(self):
        with open(settings.METRICS_FILE, "wb") as f:
            f.truncate(0)

    def read_all(self) -> List[dict]:
        metrics = []
        with open(settings.METRICS_FILE, "rb") as f:
            unpacker = msgpack.Unpacker(f, raw=False)
            for batch in unpacker:
                for item in batch:
                    metrics.append(MetricPoint(**item).model_dump())
        return metrics

file_service = FileService()
