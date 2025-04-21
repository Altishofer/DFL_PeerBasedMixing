import asyncio
import pickle
import logging
import zlib
import numpy as np
from collections import defaultdict
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_digits
from sklearn.neural_network import MLPClassifier
from sklearn.exceptions import ConvergenceWarning
import warnings

warnings.filterwarnings("ignore", category=ConvergenceWarning)


class ModelHandler:
    def __init__(self, node_id, total_peers):
        self._model = MLPClassifier(
            hidden_layer_sizes=(64,),
            alpha=1e-4,
            max_iter=20,
            random_state=node_id,
            warm_start=True
        )
        self._X, self._y, self._X_val, self._y_val = self._load_partition(node_id, total_peers)

    def train(self):
        logging.info(f"Started training...")
        self._model.fit(self._X, self._y)
        return self.evaluate()

    def evaluate(self):
        return self._model.score(self._X_val, self._y_val)

    def set_model(self, model):
        self._model.coefs_ = model.coefs_
        self._model.intercepts_ = model.intercepts_

    def get_model(self):
        return self._model

    def aggregate(self, models):
        coefs = [m.coefs_ for m in models]
        intercepts = [m.intercepts_ for m in models]
        self._model.coefs_ = [np.mean([m[i] for m in coefs], axis=0) for i in range(len(coefs[0]))]
        self._model.intercepts_ = [np.mean([b[i] for b in intercepts], axis=0) for i in range(len(intercepts[0]))]

    def serialize_model(self):
        return zlib.compress(pickle.dumps(self._model))

    def deserialize_model(self, byte_data):
        return pickle.loads(zlib.decompress(byte_data))

    def chunk(self, data, chunk_size):
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    def _load_partition(self, node_id, total_peers, val_ratio=0.2):
        data = load_digits()
        X = data.data
        y = data.target

        np.random.seed(42)
        indices = np.random.permutation(len(X))

        val_size = int(len(indices) * val_ratio)

        val_indices = indices[:val_size]
        train_indices = indices[val_size:]

        partition_size = len(train_indices) // total_peers
        start = node_id * partition_size
        end = len(train_indices) if node_id == total_peers - 1 else start + partition_size
        selected = train_indices[start:end]

        return X[selected], y[selected], X[val_indices], y[val_indices]


class MessageManager:
    def __init__(self, node_id, total_peers, transport, model_handler):
        self._node_id = node_id
        self._total_peers = total_peers
        self._transport = transport
        self._model_handler = model_handler
        self._incoming_parts = defaultdict(lambda: defaultdict(dict))
        self._model_buffer = defaultdict(list)
        self._final_done_buffer = set()
        self._ready_set = defaultdict(lambda: set())

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

        logging.info(f"Sent model in {len(chunks)} parts each")

    async def send_ready(self, current_round):
        msg = {
            "type": "ready",
            "round": current_round,
            "sender": self._node_id
        }
        for peer_id in range(self._total_peers):
            if peer_id != self._node_id:
                await self._transport.send(pickle.dumps(msg), peer_id)
        logging.info(f"Declared ready for aggregation")

    async def collect_models(self, current_round, own_model):
        self._ready_set[current_round].add(self._node_id)
        self._model_buffer[current_round].append(own_model)

        while len(self._model_buffer[current_round]) < self._total_peers and len(self._ready_set[current_round]) < self._total_peers:
            msg = await self._transport.receive()
            parsed = pickle.loads(msg)

            if parsed["type"] == "model_part":
                sender = parsed["sender"]
                part_idx = parsed["part_idx"]
                total_parts = parsed["total_parts"]
                msg_round = parsed["round"]
                self._incoming_parts[msg_round][sender][part_idx] = parsed["data"]

                current_parts = self._incoming_parts[current_round][sender]
                logging.debug(f"Received part {part_idx+1}/{total_parts} from Node {sender} for round {msg_round}")

                if len(current_parts) == total_parts and set(current_parts.keys()) == set(range(total_parts)):
                    full_data = b"".join(current_parts[i] for i in range(total_parts))
                    model = self._model_handler.deserialize_model(full_data)
                    self._model_buffer[current_round].append(model)
                    logging.info(f"Reassembled full model from Node {sender} for round {msg_round}")

            elif parsed["type"] == "ready":
                sender = parsed["sender"]
                msg_round = parsed["round"]
                self._ready_set[msg_round].add(sender)
                logging.info(f"Ready from Node {sender} for round {msg_round} ({len(self._ready_set[msg_round])}/{self._total_peers})")

            elif parsed["type"] == "final_done":
                sender = parsed["sender"]
                self._final_done_buffer.add(sender)
                logging.debug(f"Buffered early final_done from Node {sender}")

        return self._model_buffer[current_round]

    async def sync_final_round(self):
        final_done = {self._node_id} | self._final_done_buffer
        msg = {
            "type": "final_done",
            "sender": self._node_id
        }
        for peer_id in range(self._total_peers):
            if peer_id != self._node_id:
                await self._transport.send(pickle.dumps(msg), peer_id)

        while len(final_done) < self._total_peers:
            msg = await self._transport.receive()
            parsed = pickle.loads(msg)
            if parsed.get("type") == "final_done":
                sender = parsed["sender"]
                if sender not in final_done:
                    final_done.add(sender)
                    logging.info(f"Final done received from Node {sender} ({len(final_done)}/{self._total_peers})")

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
            await self._message_manager.send_ready(self._current_round)
            self._current_round += 1

        logging.info(f"Completed all {self._total_rounds} training rounds")
        await self._message_manager.sync_final_round()
        await asyncio.sleep(10)


    def _log_header(self, title):
        logging.info(f"\n{'=' * 20} {title} {'=' * 20}")

    def _log_footer(self, acc_before, acc_after):
        val_acc = self._model_handler.evaluate()
        delta = acc_after - acc_before
        logging.info(
            f"Round {self._current_round} done | "
            f"Train: {acc_before:.4f} ➜ {acc_after:.4f} | Δ: {delta:+.4f} | "
            f"[Validation Accuracy: {val_acc:.4f}]"
        )
        logging.info("=" * 60)