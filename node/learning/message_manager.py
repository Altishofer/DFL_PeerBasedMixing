import asyncio
import logging
import time

from utils.exception_decorator import log_exceptions
from communication.packages import PackageHelper

class MessageManager:
    def __init__(self, node_id, transport, model_handler):
        self._node_id = node_id
        self._transport = transport
        self._model_handler = model_handler

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
        chunks, n_chunks = self.chunks()
        n_peers = 0
        for i in range(n_chunks):
            n_peers = await self.send_model_chunk(current_round, i, chunks[i], n_chunks)
        logging.info(f"Sent {n_chunks} model chunks to {n_peers} peers.")

    async def send_model_chunk(self, current_round, chunk_idx, chunk, n_chunks):
        msg = PackageHelper.format_model_package(current_round, chunk_idx, chunk, n_chunks)
        return await self._transport.send_to_peers(msg)

    async def await_fragments(self, timeout: int):

        all_surbs_received = all_fragments_received = False
        start_time = time.time()
        while True:

            if not all_surbs_received:
                all_surbs_received = await self._transport.sphinx_router.router_all_acked()

            if not all_fragments_received:
                all_fragments_received = await self._transport.received_all_expected_fragments()

            if time.time() - start_time > timeout:
                logging.warning("Timeout reached while waiting for fragments.")
                break

            await asyncio.sleep(5)

    @log_exceptions
    async def collect_models(self):
        buffer = []
        collected_parts = 0

        fragments = self._transport.get_all_fragments()

        for msg in fragments:
            collected_parts += 1

            logging.debug(f"Collected {collected_parts} model parts.")

            part_idx = msg["part_idx"]
            total_parts = msg["total_parts"]
            msg_round = msg["round"]

            buffer.append(msg["content"])
            logging.debug(f"Received part {part_idx + 1}/{total_parts} for round {msg_round}")

        active_nodes = self._transport.active_nodes()
        logging.info(
            f"Received total {collected_parts} parts from {active_nodes} nodes."
            f"({collected_parts / active_nodes if active_nodes else 0:.2f} parts/node)"
        )
        return buffer

