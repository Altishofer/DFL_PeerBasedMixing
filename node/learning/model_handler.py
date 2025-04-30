import pickle
import logging
import zlib
import numpy as np
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


