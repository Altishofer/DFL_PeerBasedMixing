import asyncio
import logging
import time

from learning.message_manager import MessageManager
from learning.model_handler import ModelHandler
from metrics.node_metrics import metrics, MetricField
from models.schemas import NodeConfig
from utils.logging_config import log_exceptions, log_header
from utils.config_store import ConfigStore


class Learner:

    def __init__(self, node_config : NodeConfig, transport):
        self._node_id = node_config.node_id
        self._transport = transport
        self._total_peers = node_config.n_nodes
        self._total_rounds = node_config.rounds
        self._current_round = 0
        self._model_handler = ModelHandler(self._node_id, self._total_peers)
        self._message_manager = MessageManager(self._node_id, transport, self._model_handler)
        self._stream_based = node_config.stream
        self._exit_node = node_config.exit
        self._join_node = node_config.join

    @log_exceptions
    async def run(self):
        aggregated_accuracy = float()
        start = time.time()

        while self._current_round <= self._total_rounds:

            self._current_round += 1

            metrics().set(MetricField.CURRENT_ROUND, self._current_round)
            log_header(f"ROUND {self._current_round}")
            logging.info(f"Stream Mode: {self._stream_based}")

            # update_task = None
            # if self._stream_based:
            #     update_task = asyncio.create_task(
            #         self._message_manager.stream_model(self._current_round, 0.2)
            #     )

            log_header(f"Start Training")
            await asyncio.to_thread(self._model_handler.train)
            logging.info(f"Finished Training")

            # if update_task:
            #     await update_task
            logging.info(f"Broadcasting Model Updates")
            if not self._stream_based:
                await self._message_manager.send_model_updates(self._current_round)

            log_header("Local Model Validation Accuracy")
            accuracy = await asyncio.to_thread(self._model_handler.evaluate)
            logging.info(f"Acc. {aggregated_accuracy:.2f} ➜ {accuracy:.2f} | Δ: {accuracy - aggregated_accuracy:+.2f}")
            metrics().set(MetricField.ACCURACY, accuracy)

            log_header(f"Awaiting Model Chunks from Peers ({ConfigStore.timeout_model_collection}s).")
            await asyncio.sleep(ConfigStore.timeout_model_collection)
            model_chunks, highest_peer_round = self._message_manager.collect_models()

            log_header(f"Aggregating {len(model_chunks)} Model Chunks.")
            self._model_handler.aggregate(model_chunks)

            log_header("Aggregated Model Validation Accuracy")
            accuracy = await asyncio.to_thread(self._model_handler.evaluate)
            logging.info(f"acc {aggregated_accuracy:.2f} ➜ {accuracy:.2f} | Δ: {accuracy - aggregated_accuracy:+.2f}")
            aggregated_accuracy = accuracy
            metrics().set(MetricField.AGGREGATED_ACCURACY, accuracy)

            log_header(f"Finished Round {self._current_round}")
            logging.info(f"Finished in {time.time() - start:.0f}s")
            start = time.time()

        logging.info(f"Completed all {self._total_rounds} training rounds")

