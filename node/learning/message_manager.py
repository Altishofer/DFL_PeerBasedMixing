import asyncio
import hashlib
import logging
import pickle
import zlib
from utils.exception_decorator import log_exceptions

class MessageManager:
    def __init__(self, node_id, transport, model_handler):
        self._node_id = node_id
        self._transport = transport
        self._model_handler = model_handler
        self._seen_hashes = set()

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
        n_peers = 0
        for i in range(n_chunks):
            n_peers = await self.send_model_chunk(current_round, i, chunks[i], n_chunks)
        logging.info(f"Sent {n_chunks} model chunks to {n_peers} peers.")

    async def send_model_chunk(self, current_round, chunk_idx, chunk, n_chunks):
        msg = {
            "type": "model_part",
            "round": current_round,
            "part_idx": chunk_idx,
            "total_parts": n_chunks,
            "content": chunk
        }
        serialized_msg = self._serialize_msg(msg)
        return await self._transport.send_to_peers(serialized_msg)

    @log_exceptions
    def collect_models(self):
        buffer = []
        collected_parts = max_round = 0

        fragments = self._transport.get_all_fragments()

        for msg in fragments:
            msg_hash = hashlib.sha256(msg).digest()
            if msg_hash in self._seen_hashes:
                logging.warning("Duplicate fragment dropped.")
                continue
            self._seen_hashes.add(msg_hash)

            parsed = self._deserialize_msg(msg)
            collected_parts += 1

            logging.debug(f"Collected {collected_parts} model parts.")

            if parsed["type"] == "model_part":
                part_idx = parsed["part_idx"]
                total_parts = parsed["total_parts"]
                msg_round = parsed["round"]
                max_round = max(max_round, msg_round)

                buffer.append(parsed["content"])
                logging.debug(f"Received part {part_idx + 1}/{total_parts} for round {msg_round}")

        active_nodes = self._transport.active_nodes()
        logging.info(
            f"Received total {collected_parts} parts from {active_nodes} "
            f"({collected_parts / active_nodes if active_nodes else 0:.2f} parts/node)"
        )
        return buffer, max_round

    @log_exceptions
    def _serialize_msg(self, msg) -> bytes:
        return zlib.compress(pickle.dumps(msg))

    @log_exceptions
    def _deserialize_msg(self, msg) -> dict:
        return pickle.loads(zlib.decompress(msg))
