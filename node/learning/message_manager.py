import logging
import pickle
from asyncio import get_running_loop, sleep, QueueEmpty
from collections import defaultdict
import zlib
from utils.exception_decorator import log_exceptions

class MessageManager:
    def __init__(self, node_id, total_peers, transport, model_handler):
        self._node_id = node_id
        self._total_peers = total_peers
        self._transport = transport
        self._model_handler = model_handler
        self._incoming_parts = []
        self._model_chunk_buffer = defaultdict(list)
        self._chunk_size = 600

    @log_exceptions
    async def send_model_updates(self, current_round, interval):
        # TODO: implement some early stopping?

        self._model_handler.create_chunks(self._model_handler.get_model(), self._chunk_size)

        model = self._model_handler.get_model()
        self._model_handler.create_chunks(model, self._chunk_size)
        chunks = self._model_handler.get_chunks()
        n_chunks = len(chunks)

        for i in range(n_chunks):
            await self.send_model_chunk(current_round, i, chunks[i], n_chunks)

    async def send_model_chunk(self, current_round, chunk_idx, chunk, n_chunks):
        for peer_id in range(self._total_peers):
            if peer_id == self._node_id:
                continue

            msg = {
                "type": "model_part",
                "round": current_round,
                "part_idx": chunk_idx,
                "total_parts": n_chunks,
                "content": chunk
            }
            serialized_msg = self._serialize_msg(msg)

            for peer_id in range(self._total_peers):
                if peer_id != self._node_id:
                    await self._transport.send(serialized_msg, peer_id)

        logging.info(f"Sent model chunk {chunk_idx}")

    @log_exceptions
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

    @log_exceptions
    def _serialize_msg(self, msg):
        return zlib.compress(pickle.dumps(msg))

    @log_exceptions
    def _deserialize_msg(self, msg):
        return pickle.loads(zlib.decompress(msg))
