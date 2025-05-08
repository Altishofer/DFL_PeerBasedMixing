import logging
import pickle
from asyncio import get_running_loop, sleep, QueueEmpty
from collections import defaultdict
import zlib

class MessageManager:
    def __init__(self, node_id, total_peers, transport, model_handler):
        self._node_id = node_id
        self._total_peers = total_peers
        self._transport = transport
        self._model_handler = model_handler
        self._incoming_parts = []
        self._model_chunk_buffer = defaultdict(list)

    async def send_model(self, current_round):
        model = self._model_handler.get_model()
        coef, intercepts = self._model_handler.chunk_model(model, 600)
        chunks = coef + intercepts

        for peer_id in range(self._total_peers):
            if peer_id == self._node_id:
                continue
            for idx, chunk in enumerate(chunks):
                msg = {
                    "type": "model_part",
                    "round": current_round,
                    "part_idx": idx,
                    "total_parts": len(chunks),
                    "content": chunk
                }
                await self._transport.send(self._serialize_msg(msg), peer_id)

        logging.info(f"Sent model in {len(chunks)} parts each")

    async def collect_models(self, current_round):
        #TODO: better stopping condition
        t = 30.0
        start_time = get_running_loop().time()
        while get_running_loop().time() - start_time < t:
            try:
                msg = self._transport._incoming_queue.get_nowait()
                parsed = self._deserialize_msg(msg)

                if parsed["type"] == "model_part":
                    part_idx = parsed["part_idx"]
                    total_parts = parsed["total_parts"]
                    msg_round = parsed["round"]

                    self._model_chunk_buffer[current_round].append(parsed["content"])
                    logging.debug(f"Received part {part_idx+1}/{total_parts} for round {msg_round}")
            except QueueEmpty:
                await sleep(0.1)
                    
        logging.debug("Finished collecting models")
        return self._model_chunk_buffer[current_round]
    
    def _serialize_msg(self, msg):
        return zlib.compress(pickle.dumps(msg))
    
    def _deserialize_msg(self, msg):
        return pickle.loads(zlib.decompress(msg))
