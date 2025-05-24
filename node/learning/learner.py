import asyncio
import logging

from learning.message_manager import MessageManager
from learning.model_handler import ModelHandler
from metrics.node_metrics import metrics, MetricField
from models.schemas import NodeConfig
from utils.logging_config import log_exceptions


class Learner:
    def __init__(self, node_config : NodeConfig, transport):
        self._node_id = node_config.node_id
        self._transport = transport
        self._total_peers = node_config.n_nodes
        self._total_rounds = node_config.rounds
        self._current_round = 0
        self._model_handler = ModelHandler(self._node_id, self._total_peers)
        self._message_manager = MessageManager(self._node_id, self._total_peers, transport, self._model_handler)
        self._stream_based = node_config.stream

    @log_exceptions
    async def run(self):
        while self._current_round < self._total_rounds:
            metrics().set(MetricField.CURRENT_ROUND, self._current_round)
            self._log_header(f"ROUND {self._current_round}")
            self._log_header(f"Stream model updates {self._stream_based}")
            update_task = None
            if self._stream_based:
                update_task = asyncio.create_task(
                    self._message_manager.stream_model(self._current_round, 0.2)
                )
            acc_before = self._model_handler.train()

            if update_task:
                await update_task

            if not self._stream_based:
                await self._message_manager.send_model_updates(self._current_round)

            model_chunks = await self._message_manager.collect_models(self._current_round)
            self._model_handler.aggregate(model_chunks)
            acc_after = self._model_handler.evaluate()
            self._log_footer(acc_before, acc_after)
            self._current_round += 1

        logging.info(f"Completed all {self._total_rounds} training rounds")
        await asyncio.sleep(10)

    def _log_header(self, title):
        logging.info(f"\n{'=' * 20} {title} {'=' * 20}")

    def _log_footer(self, acc_before, acc_after):
        val_acc = self._model_handler.evaluate()
        delta = acc_after - acc_before
        logging.info(f"Round {self._current_round} done")
        logging.info(f"Train: {acc_before:.4f} ➜ {acc_after:.4f} | Δ: {delta:+.4f}")
        logging.info(f"Validation Accuracy: {val_acc:.4f}")
        logging.info("=" * 60)
