import pickle
import zlib
from enum import Enum

class PackageType(Enum):
    MODEL_PART = 1
    COVER = 2
    ROUND_FINISHED = 3

class PackageHelper:
    @staticmethod
    def format_model_package(current_round, chunk_idx, chunk, n_chunks):
        return {
            "type": PackageType.MODEL_PART,
            "round": current_round,
            "part_idx": chunk_idx,
            "total_parts": n_chunks,
            "content": chunk
        }

    @staticmethod
    def format_cover_package(content):
        return {
            "type": PackageType.COVER,
            "content": content
        }
    
    @staticmethod
    def serialize_msg(msg) -> bytes:
        return zlib.compress(pickle.dumps(msg))

    @staticmethod
    def deserialize_msg(msg) -> dict:
        return pickle.loads(zlib.decompress(msg))
