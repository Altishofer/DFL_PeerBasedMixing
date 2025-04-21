import asyncio
import pickle
import logging
import zlib
import numpy as np
from collections import defaultdict
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_digits


class ModelHandler:
    def __init__(self, node_id, total_peers):
        self._model = LogisticRegression(max_iter=1000)
        self._X, self._y = self._load_partition(node_id, total_peers)

    def train(self):
        self._model.fit(self._X, self._y)
        return self.evaluate()

    def evaluate(self):
        return self._model.score(self._X, self._y)

    def get_model(self):
        return self._model

    def set_model(self, model):
        self._model.coef_ = model.coef_

    def aggregate(self, models):
        coefs = [m.coef_ for m in models]
        self._model.coef_ = np.mean(coefs, axis=0)

    def serialize_model(self):
        return zlib.compress(pickle.dumps(self._model))

    def deserialize_model(self, byte_data):
        return pickle.loads(zlib.decompress(byte_data))

    def chunk(self, data, chunk_size):
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    def _load_partition(self, node_id, total_peers):
        data = load_digits()
        X = data.data
        y = data.target
        label_indices = defaultdict(list)
        for i, label in enumerate(y):
            label_indices[label].append(i)

        selected = []
        for label, indices in label_indices.items():
            indices.sort()
            chunk_size = len(indices) // total_peers
            start = node_id * chunk_size
            end = len(indices) if node_id == total_peers - 1 else start + chunk_size
            selected.extend(indices[start:end])

        return X[selected], y[selected]


class MessageManager:
    def __init__(self, node_id, total_peers, transport, model_handler):
        self._node_id = node_id
        self._total_peers = total_peers
        self._transport = transport
        self._model_handler = model_handler
        self._incoming_parts = defaultdict(lambda: defaultdict(dict))
        self._ready_set = set()
        self._model_buffer = defaultdict(list)

    async def send_model(self, current_round):
        model_data = self._model_handler.serialize_model()
        chunks = self._model_handler.chunk(model_data, 700)

        for peer_id in range(self._total_peers):
            if peer_id == self._node_id:
                continue
            for idx, chunk in enumerate(chunks):
                msg = {
                    "type": "model_part",
                    "round": current_round,
                    "sender": self._node_id,
                    "part_idx": idx,
                    "total_parts": len(chunks),
                    "data": chunk
                }
                await self._transport.send(pickle.dumps(msg), peer_id)

        logging.info(f"📤 Sent model in {len(chunks)} parts")

    async def send_ready(self, current_round):
        msg = {
            "type": "ready",
            "round": current_round,
            "sender": self._node_id
        }
        for peer_id in range(self._total_peers):
            if peer_id != self._node_id:
                await self._transport.send(pickle.dumps(msg), peer_id)
        logging.info(f"✅ Declared ready for aggregation")

    async def collect_models(self, current_round, own_model):
        self._ready_set = {self._node_id}
        self._model_buffer[current_round].append(own_model)

        while len(self._ready_set) < self._total_peers:
            msg = await self._transport.receive()
            parsed = pickle.loads(msg)

            if parsed.get("round") != current_round:
                continue

            if parsed["type"] == "model_part":
                sender = parsed["sender"]
                part_idx = parsed["part_idx"]
                total_parts = parsed["total_parts"]
                self._incoming_parts[current_round][sender][part_idx] = parsed["data"]

                current_parts = self._incoming_parts[current_round][sender]
                logging.info(f"📦 Received part {part_idx+1}/{total_parts} from Node {sender}")

                if len(current_parts) == total_parts and set(current_parts.keys()) == set(range(total_parts)):
                    full_data = b"".join(current_parts[i] for i in range(total_parts))
                    model = self._model_handler.deserialize_model(full_data)
                    self._model_buffer[current_round].append(model)
                    logging.info(f"✅ Reassembled full model from Node {sender}")
                    await self.send_ready(current_round)

            elif parsed["type"] == "ready":
                sender = parsed["sender"]
                self._ready_set.add(sender)
                logging.info(f"🟢 Ready from Node {sender} ({len(self._ready_set)}/{self._total_peers})")

        return self._model_buffer[current_round]


class Learning:
    def __init__(self, node_id, transport, total_peers, total_rounds=5):
        self._node_id = node_id
        self._transport = transport
        self._total_peers = total_peers
        self._total_rounds = total_rounds
        self._current_round = 0
        self._model_handler = ModelHandler(node_id, total_peers)
        self._message_manager = MessageManager(node_id, total_peers, transport, self._model_handler)

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

        logging.info(f"✅ Completed all {self._total_rounds} training rounds")

    def _log_header(self, title):
        logging.info(f"\n{'=' * 20} {title} {'=' * 20}")

    def _log_footer(self, acc_before, acc_after):
        delta = acc_after - acc_before
        logging.info(
            f"✅ Round {self._current_round} done | "
            f"Accuracy: {acc_before:.4f} ➜ {acc_after:.4f} | Δ: {delta:+.4f}"
        )
        logging.info("=" * 60)