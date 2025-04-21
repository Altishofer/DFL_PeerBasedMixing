import asyncio
import pickle
import logging
import zlib
import numpy as np
from collections import defaultdict
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_digits


class Learning:
    def __init__(self, node_id, transport, total_peers, total_rounds=5):
        self._node_id = node_id
        self._transport = transport
        self._model = LogisticRegression(max_iter=1000)
        self._X, self._y = self._load_partition(total_peers)
        self._total_peers = total_peers
        self._total_rounds = total_rounds
        self._current_round = 0
        self._model_buffer = {}
        self._ready_set = set()
        self._incoming_parts = defaultdict(lambda: defaultdict(dict))  # round -> sender -> {part_idx: chunk}

    def _load_partition(self, total_peers):
        data = load_digits()
        X = data.data
        y = data.target
        label_indices = defaultdict(list)
        for i, label in enumerate(y):
            label_indices[label].append(i)

        selected_indices = []
        for label, indices in label_indices.items():
            indices.sort()
            chunk_size = len(indices) // total_peers
            start = self._node_id * chunk_size
            end = start + chunk_size if self._node_id < total_peers - 1 else len(indices)
            selected_indices.extend(indices[start:end])

        return X[selected_indices], y[selected_indices]

    async def run(self):
        while self._current_round < self._total_rounds:
            self._log_header(f"ROUND {self._current_round}")
            acc_before = self._train()
            await self._send_model()
            await self._send_ready()
            await self._collect_for_round()
            self._aggregate()
            acc_after = self._evaluate()
            self._log_footer(acc_before, acc_after)
            self._current_round += 1

        logging.info(f"[Node {self._node_id}] ✅ Completed all {self._total_rounds} training rounds")

    def _train(self):
        self._model.fit(self._X, self._y)
        acc = self._model.score(self._X, self._y)
        logging.info(f"[Node {self._node_id}] 📈 Trained | Accuracy before agg: {acc:.4f}")
        return acc

    def _chunk_bytes(self, data: bytes, chunk_size: int):
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    async def _send_model(self):
        raw = zlib.compress(pickle.dumps(self._model))
        chunks = self._chunk_bytes(raw, 700)

        for idx, chunk in enumerate(chunks):
            msg = {
                "type": "model_part",
                "round": self._current_round,
                "sender": self._node_id,
                "part_idx": idx,
                "total_parts": len(chunks),
                "data": chunk
            }
            await self._transport.send(pickle.dumps(msg))

        logging.info(f"[Node {self._node_id}] 📤 Sent model in {len(chunks)} parts")

    async def _send_ready(self):
        msg = {
            "type": "ready",
            "round": self._current_round,
            "sender": self._node_id
        }
        await self._transport.send(pickle.dumps(msg))
        logging.info(f"[Node {self._node_id}] ✅ Declared ready for aggregation")

    async def _collect_for_round(self):
        r = self._current_round
        self._model_buffer.setdefault(r, [self._model])
        self._ready_set = {self._node_id}

        while len(self._ready_set) < self._total_peers:
            msg = await self._transport.receive()
            parsed = pickle.loads(msg)

            mtype = parsed.get("type")
            sender = parsed.get("sender")
            round_num = parsed.get("round")

            if round_num != r:
                continue

            if mtype == "model_part":
                part_idx = parsed["part_idx"]
                total_parts = parsed["total_parts"]
                chunk = parsed["data"]

                self._incoming_parts[r][sender][part_idx] = chunk
                current = len(self._incoming_parts[r][sender])

                logging.info(
                    f"[Node {self._node_id}] 📦 Received part {part_idx+1}/{total_parts} from Node {sender}"
                )

                if current == total_parts:
                    ordered = [self._incoming_parts[r][sender][i] for i in range(total_parts)]
                    model_bytes = b"".join(ordered)
                    model = pickle.loads(zlib.decompress(model_bytes))
                    self._model_buffer[r].append(model)
                    logging.info(f"[Node {self._node_id}] ✅ Reassembled full model from Node {sender}")

            elif mtype == "ready":
                self._ready_set.add(sender)
                logging.info(
                    f"[Node {self._node_id}] 🟢 Ready from Node {sender} "
                    f"({len(self._ready_set)}/{self._total_peers})"
                )

    def _aggregate(self):
        models = self._model_buffer[self._current_round]
        coefs = [model.coef_ for model in models]
        self._model.coef_ = np.mean(coefs, axis=0)
        logging.info(f"[Node {self._node_id}] 🧠 Aggregated {len(models)} models")

    def _evaluate(self):
        acc = self._model.score(self._X, self._y)
        return acc

    def _log_header(self, title):
        logging.info(f"\n{'=' * 20} {title} {'=' * 20}")

    def _log_footer(self, acc_before, acc_after):
        delta = acc_after - acc_before
        logging.info(
            f"[Node {self._node_id}] ✅ Round {self._current_round} done | "
            f"Accuracy: {acc_before:.4f} ➜ {acc_after:.4f} | Δ: {delta:+.4f}"
        )
        logging.info("=" * 60)