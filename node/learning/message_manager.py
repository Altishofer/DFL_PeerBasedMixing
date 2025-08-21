import asyncio
import logging
import time

from communication.packages import PackageHelper
from communication.sphinx.sphinx_transport import SphinxTransport
from learning.model_handler import ModelHandler
from utils.config_store import ConfigStore
from utils.exception_decorator import log_exceptions


class MessageManager:
    def __init__(self, node_id, transport: SphinxTransport, model_handler: ModelHandler, node_config: ConfigStore):
        self._node_id = node_id
        self._transport = transport
        self._model_handler = model_handler
        self._node_config = node_config

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
        self._transport.n_fragments_per_model = n_chunks
        n_peers = 0
        for i in range(n_chunks):
            n_peers = await self.send_model_chunk(current_round, i, chunks[i], n_chunks)
        logging.info(f"Sent {n_chunks} model chunks to {n_peers} peers.")

    async def send_model_chunk(self, current_round, chunk_idx, chunk, n_chunks):
        msg = PackageHelper.format_model_package(current_round, chunk_idx, chunk, n_chunks)
        return await self._transport.send_to_peers(msg)

    async def await_fragments(self, timeout: int):
        start_time = time.time()

        while not await self._transport.received_all_expected_fragments() and time.time() - start_time < timeout:
            await asyncio.sleep(5)

        while not await self._transport.sphinx_router.router_all_acked() and time.time() - start_time < timeout:
            await asyncio.sleep(5)

        if time.time() - start_time > timeout:
            logging.warning(f"Timeout of {timeout} reached while waiting for fragments.")
            return

        logging.info(f"All fragments and SURBs received after {int(time.time() - start_time)}s, early stopping.")

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

            if collected_parts > self._transport.active_nodes() * self._transport.n_fragments_per_model:
                self._transport.push_unexpected_to_queue(msg)
            else:
                buffer.append(msg["content"])
                logging.debug(f"Received part {part_idx + 1}/{total_parts}.")

        active_nodes = self._transport.active_nodes()
        logging.info(
            f"Received total {collected_parts} parts from {active_nodes} nodes."
            f"({collected_parts / active_nodes if active_nodes else 0:.2f} parts/node)"
        )
        return buffer
