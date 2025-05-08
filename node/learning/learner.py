import asyncio
import logging

from node.learning.message_manager import MessageManager
from node.learning.model_handler import ModelHandler
from utils.exception_decorator import log_exceptions


class Learner:
    def __init__(self, node_id, transport, total_peers, total_rounds=30):
        self._node_id = node_id
        self._transport = transport
        self._total_peers = total_peers
        self._total_rounds = total_rounds
        self._current_round = 0
        self._model_handler = ModelHandler(node_id, total_peers)
        self._message_manager = MessageManager(node_id, total_peers, transport, self._model_handler)

    @log_exceptions
    async def run(self):
        while self._current_round < self._total_rounds:
            self._log_header(f"ROUND {self._current_round}")
            acc_before = self._model_handler.train()
            await self._message_manager.send_model(self._current_round)
            models = await self._message_manager.collect_models(self._current_round, self._model_handler.get_model())
            self._model_handler.aggregate(models)
            acc_after = self._model_handler.evaluate()
            self._log_footer(acc_before, acc_after)
            self._current_round += 1

        logging.info(f"Completed all {self._total_rounds} training rounds")
        await asyncio.sleep(10)

    @log_exceptions
    def _log_header(self, title):
        logging.info(f"\n{'=' * 20} {title} {'=' * 20}")

    @log_exceptions
    def _log_footer(self, acc_before, acc_after):
        val_acc = self._model_handler.evaluate()
        delta = acc_after - acc_before
        logging.info(
            f"Round {self._current_round} done | "
            f"Train: {acc_before:.4f} ➜ {acc_after:.4f} | Δ: {delta:+.4f} | "
            f"[Validation Accuracy: {val_acc:.4f}]"
        )
