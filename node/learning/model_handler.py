import pickle
import logging
import zlib
import numpy as np
from sklearn.datasets import load_digits
from sklearn.neural_network import MLPClassifier
from sklearn.exceptions import ConvergenceWarning
import warnings
from math import ceil

from utils.exception_decorator import log_exceptions

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

    @log_exceptions
    def train(self):
        logging.info(f"Started training...")
        self._model.fit(self._X, self._y)
        return self.evaluate()

    @log_exceptions
    def evaluate(self):
        return self._model.score(self._X_val, self._y_val)

    @log_exceptions
    def set_model(self, model):
        self._model.coefs_ = model.coefs_
        self._model.intercepts_ = model.intercepts_

    @log_exceptions
    def get_model(self):
        return self._model
    
    def _aggregate_chunk(self, chunk, aggregate, counter):
        aggregate[chunk["start"]:chunk["end"]] += chunk["data"]
        counter[chunk["start"]:chunk["end"]] += 1

<<<<<<< HEAD
    @log_exceptions
    def aggregate(self, models):
        coefs = [m.coefs_ for m in models]
        intercepts = [m.intercepts_ for m in models]
        self._model.coefs_ = [np.mean([m[i] for m in coefs], axis=0) for i in range(len(coefs[0]))]
        self._model.intercepts_ = [np.mean([b[i] for b in intercepts], axis=0) for i in range(len(intercepts[0]))]

    @log_exceptions
    def serialize_model(self):
        return zlib.compress(pickle.dumps(self._model))

    @log_exceptions
    def deserialize_model(self, byte_data):
        return pickle.loads(zlib.decompress(byte_data))

    @log_exceptions
    def chunk(self, data, chunk_size):
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    @log_exceptions
=======
    def aggregate(self, model_chunks):
        agg_coefs = self._flatten(self._model.coefs_)
        agg_intercepts = self._flatten(self._model.intercepts_)
        n_coefs = np.ones(len(agg_coefs), dtype=int)
        n_intercepts = np.ones(len(agg_intercepts), dtype=int)

        for chunk in model_chunks:
            if chunk["type"] == "coef":
                self._aggregate_chunk(chunk, agg_coefs, n_coefs)
            elif chunk["type"] == "intercept":
                self._aggregate_chunk(chunk, agg_intercepts, n_intercepts)

        self._model.coefs_ = self._unflatten_coefs(agg_coefs / n_coefs, self._model)
        self._model.intercepts_ = self._unflatten_intercepts(agg_intercepts / n_intercepts, self._model)

    def _flatten(self, ls):
       return np.concatenate([arr.ravel() for arr in ls])
    
    def _unflatten_coefs(self, flat_coefs, model):
        coefs = []
        pointer = 0
        for layer_weights in model.coefs_:
            size = layer_weights.size
            shape = layer_weights.shape
            coefs.append(flat_coefs[pointer:pointer + size].reshape(shape))
            pointer += size

        return coefs
    
    def _unflatten_intercepts(self, flat_intercepts, model):
        intercepts = []

        pointer = 0
        for layer_biases in model.intercepts_:
            size = layer_biases.size
            shape = layer_biases.shape
            intercepts.append(flat_intercepts[pointer:pointer + size].reshape(shape))
            pointer += size

        return intercepts

    def _chunk_array(self, data, type, chunk_size):
        pkgs = []
        i = 0
        while i < len(data):
            elems = 1
            while True:
                end = min(i + elems, len(data))
                package = {}
                package["type"] = type
                package["start"] = i
                package["end"] = end
                package["data"] = data[i:end]
                pkg = pickle.dumps(package)
                if len(pkg) > chunk_size:
                    if elems == 1:
                        raise ValueError("Single element too large to fit in chunk")
                    elems -= 1  # back off to last valid size
                    break
                if end == len(data):
                    break
                elems += 1

            end = i + elems
            package["end"] = end
            package["data"] = data[i:end]
            pkgs.append(package)
            i = end

        return pkgs

    def chunk_model(self, data, chunk_size):
        coefs = self._flatten(data.coefs_)
        intercepts = self._flatten(data.intercepts_)

        coef_chunks = self._chunk_array(coefs, "coef", chunk_size)
        intercept_chunks = self._chunk_array(intercepts, "intercept", chunk_size)
            
        return coef_chunks, intercept_chunks
    
>>>>>>> linn
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


