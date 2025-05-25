import asyncio
import logging
import pickle
from asyncio import get_running_loop, sleep, QueueEmpty
from collections import defaultdict
import zlib
from utils.exception_decorator import log_exceptions

class MessageManager:
    def __init__(self, node_id, transport, model_handler):
        self._node_id = node_id
        self._transport = transport
        self._model_handler = model_handler
        self._incoming_parts = []
        self._model_chunk_buffer = defaultdict(list)

    @log_exceptions
    def chunks(self):
        chunks = self._model_handler.create_chunks()
        n_chunks = len(chunks)
        return chunks, n_chunks

    @log_exceptions
    async def stream_model(self, current_round, interval):
        _, n_chunks = self.chunks()
        for i in range(n_chunks):
            chunks, n_chunks = self.chunks()
            await self.send_model_chunk(current_round, i, chunks[i], n_chunks)
            await asyncio.sleep(interval)

    @log_exceptions
    async def send_model_updates(self, current_round):
        # TODO: implement some early stopping?
        chunks, n_chunks = self.chunks()
        for i in range(n_chunks):
            await self.send_model_chunk(current_round, i, chunks[i], n_chunks)

    async def send_model_chunk(self, current_round, chunk_idx, chunk, n_chunks):
        msg = {
            "type": "model_part",
            "round": current_round,
            "part_idx": chunk_idx,
            "total_parts": n_chunks,
            "content": chunk
        }
        serialized_msg = self._serialize_msg(msg)
        await self._transport.send_to_peers(serialized_msg)
        if not chunk_idx % 50:
            logging.info(f"Sent model chunk {chunk_idx} to all peers.")

    @log_exceptions
    async def collect_models(self):
        #TODO: better stopping condition
        collected_parts = max_round = 0
        time_limit = 30.0
        start_time = get_running_loop().time()
        while True:
            if get_running_loop().time() - start_time > time_limit:
                logging.info(f"Timeout of {time_limit}s reached.")
                break
            if collected_parts >= 338 * self._transport.active_nodes():
                logging.info(f"Received all parts of currently active peers.")
                break
            try:
                msg = self._transport._incoming_queue.get_nowait()
                parsed = self._deserialize_msg(msg)

                collected_parts += 1
                if collected_parts % 200 == 0:
                    logging.info(f"Collected {collected_parts} model parts.")

                if parsed["type"] == "model_part":
                    part_idx = parsed["part_idx"]
                    total_parts = parsed["total_parts"]
                    msg_round = parsed["round"]
                    max_round = max(max_round, msg_round)

                    self._model_chunk_buffer[msg_round].append(parsed["content"])
                    logging.debug(f"Received part {part_idx+1}/{total_parts} for round {msg_round}")
            except QueueEmpty:
                await sleep(0.1)

        logging.info(f"Finished collecting {collected_parts} parts from {self._transport.active_nodes()} active nodes")
        return self._model_chunk_buffer[max_round], max_round

    @log_exceptions
    def _serialize_msg(self, msg) -> bytes:
        return zlib.compress(pickle.dumps(msg))

    @log_exceptions
    def _deserialize_msg(self, msg) -> dict:
        return pickle.loads(zlib.decompress(msg))
