import pickle
import logging
import random

import numpy as np
from sklearn.datasets import load_digits
from sklearn.neural_network import MLPClassifier
from sklearn.exceptions import ConvergenceWarning
import warnings

from learning.fed_cnn import FedCNN
from utils.exception_decorator import log_exceptions
from metrics.node_metrics import metrics, MetricField

import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, Subset

import os
os.environ['TORCH_CPP_LOG_LEVEL'] = 'WARNING'




warnings.filterwarnings("ignore", category=ConvergenceWarning)


class ModelHandler:

    _BATCH_SIZE = 64
    _BATCHES_PER_ROUND = 10
    _ALPHA = 10

    def __init__(self, node_id, total_peers):
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model = FedCNN().to(self._device)
        self._loss_fn = nn.CrossEntropyLoss()
        self._optimizer = optim.Adam(self._model.parameters(), lr=1e-3)
        self._train_loader, self._val_loader = self._load_partition(node_id, total_peers)
        self._chunks = []

    @log_exceptions
    def train(self):
        logging.info(f"Start training on {self._BATCHES_PER_ROUND} random batches")
        self._model.train()
        batches = list(self._train_loader)
        random_batches = random.sample(batches, self._BATCHES_PER_ROUND)
        for Xb, yb in random_batches:
            Xb, yb = Xb.to(self._device), yb.to(self._device)
            self._optimizer.zero_grad()
            loss = self._loss_fn(self._model(Xb), yb)
            loss.backward()
            self._optimizer.step()

        return self.evaluate()

    @log_exceptions
    def evaluate(self):
        logging.info(f"Finished training, evaluating local model")
        self._model.eval()
        correct = total = 0
        with torch.no_grad():
            for Xb, yb in self._val_loader:

                Xb, yb = Xb.to(self._device), yb.to(self._device)
                pred = self._model(Xb)
                correct += (pred.argmax(1) == yb).sum().item()
                total += yb.size(0)
        accuracy = correct / total

        metrics().set(MetricField.ACCURACY, accuracy)
        return accuracy

    @log_exceptions
    def set_model(self, model):
        self._model.load_state_dict(model)

    @log_exceptions
    def get_model(self):
        return self._model.state_dict()
    
    @log_exceptions
    def _aggregate_chunk(self, chunk, aggregate, counter):
        aggregate[chunk["start"]:chunk["end"]] += chunk["data"]
        counter[chunk["start"]:chunk["end"]] += 1

    @log_exceptions
    def aggregate(self, model_chunks):
        flat = self._flatten_state_dict(self._model.state_dict())
        counter = np.ones_like(flat)

        logging.info(f"Aggregating {len(model_chunks)} chunks...")
        for chunk in model_chunks:
            if chunk["type"] == "params":
                self._aggregate_chunk(chunk, flat, counter)

        avg_flat = flat / counter
        new_state = self._unflatten_state_dict(avg_flat, self._model.state_dict())
        self._model.load_state_dict(new_state)

    def _flatten_state_dict(self, state_dict):
        return np.concatenate([param.cpu().numpy().ravel() for param in state_dict.values()])

    def _unflatten_state_dict(self, flat, reference_state_dict):
        new_state = {}
        pointer = 0
        for key, param in reference_state_dict.items():
            size = param.numel()
            shape = param.shape
            new_state[key] = torch.tensor(flat[pointer:pointer + size].reshape(shape), dtype=param.dtype)
            pointer += size
        return new_state


    @log_exceptions
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

    @log_exceptions
    def create_chunks(self, data, chunk_size):
        flat = self._flatten_state_dict(data)
        self._chunks = self._chunk_array(flat, "params", chunk_size)

    def get_chunks(self,):
        return self._chunks

    @log_exceptions
    def _load_partition(self, node_id, total_peers):
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,))
        ])
        dataset = datasets.FashionMNIST(root="/tmp/fashionmnist", train=True, transform=transform, download=True)
        val_dataset = datasets.FashionMNIST(root="/tmp/fashionmnist", train=False, transform=transform, download=True)

        labels = np.array(dataset.targets)
        num_classes = 10
        class_indices = [np.where(labels == y)[0] for y in range(num_classes)]
        per_node_indices = [[] for _ in range(total_peers)]

        for c in range(num_classes):
            indices = class_indices[c]
            np.random.shuffle(indices)
            proportions = np.random.dirichlet(alpha=np.ones(total_peers) * self._ALPHA)
            proportions = (np.cumsum(proportions) * len(indices)).astype(int)[:-1]
            splits = np.split(indices, proportions)
            for i, split in enumerate(splits):
                per_node_indices[i].extend(split)

        np.random.shuffle(per_node_indices[node_id])
        train_subset = torch.utils.data.Subset(dataset, per_node_indices[node_id])

        val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=self._BATCH_SIZE, shuffle=False)
        train_loader = torch.utils.data.DataLoader(train_subset, batch_size=self._BATCH_SIZE, shuffle=True)

        return train_loader, val_loader

