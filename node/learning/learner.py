import logging
import time

from learning.message_manager import MessageManager
from learning.model_handler import ModelHandler
from metrics.node_metrics import metrics, MetricField
from utils.config_store import ConfigStore
from utils.logging_config import log_exceptions, log_header


class Learner:

    def __init__(self, node_config: ConfigStore, transport):
        self._node_id = node_config.node_id
        self._transport = transport
        self._total_peers = node_config.n_nodes
        self._total_rounds = node_config.n_rounds
        self._current_round = 0
        self._model_handler = ModelHandler(self._node_id, self._total_peers)
        self._message_manager = MessageManager(self._node_id, transport, self._model_handler, node_config)

    @log_exceptions
    async def run(self):
        aggregated_accuracy = 0.0
        start_time = time.time()

        while self._current_round < self._total_rounds:
            self._current_round += 1
            metrics().set(MetricField.CURRENT_ROUND, self._current_round)

            self._log_round_start()
            if (not ConfigStore.pause_training):
                await self._train_model()
                await self._validate_local_model(aggregated_accuracy)
                await self._broadcast_model_updates()

            await self._await_model_chunks()

            aggregated_accuracy = await self._aggregate_and_validate_models(aggregated_accuracy)

            self._log_round_end(start_time)
            start_time = time.time()

        logging.info(f"Completed all {self._total_rounds} training rounds")

    def _log_round_start(self):
        log_header(f"ROUND {self._current_round}")

    async def _train_model(self):
        log_header("Start Training")
        metrics().set(MetricField.STAGE, 1)
        await self._model_handler.train()
        logging.info("Finished Training")

    async def _validate_local_model(self, aggregated_accuracy: float):
        log_header("Local Model Validation Accuracy")
        metrics().set(MetricField.STAGE, 2)
        accuracy = await self._model_handler.evaluate()
        logging.info(f"Acc. {aggregated_accuracy:.2f} ➜ {accuracy:.2f} | Δ: {accuracy - aggregated_accuracy:+.2f}")
        metrics().set(MetricField.TRAINING_ACCURACY, accuracy)

    async def _broadcast_model_updates(self):
        logging.info("Broadcasting Model Updates")
        await self._message_manager.send_model_updates(self._current_round)

    async def _await_model_chunks(self):
        log_header(f"Awaiting Model Chunks from Peers ({ConfigStore.timeout_model_collection}s).")
        metrics().set(MetricField.STAGE, 3)
        await self._message_manager.await_fragments(timeout=ConfigStore.timeout_model_collection)
        # await asyncio.sleep(60)

    async def _aggregate_and_validate_models(self, aggregated_accuracy: float) -> float:
        model_chunks = await self._message_manager.collect_models()
        log_header(f"Aggregating {len(model_chunks)} Model Chunks.")
        self._model_handler.aggregate(model_chunks)

        log_header("Aggregated Model Validation Accuracy")
        metrics().set(MetricField.STAGE, 4)
        accuracy = await self._model_handler.evaluate()
        metrics().set(MetricField.STAGE, 0)
        logging.info(f"Acc. {aggregated_accuracy:.2f} ➜ {accuracy:.2f} | Δ: {accuracy - aggregated_accuracy:+.2f}")
        metrics().set(MetricField.AGGREGATED_ACCURACY, accuracy)

        return accuracy

    def _log_round_end(self, start_time: float):
        log_header(f"Finished Round {self._current_round}")
        elapsed_time = time.time() - start_time
        logging.info(f"Finished in {elapsed_time:.0f}s")
        metrics().set(MetricField.ROUND_TIME, elapsed_time)
