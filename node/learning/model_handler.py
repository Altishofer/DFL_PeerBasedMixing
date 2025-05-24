import pickle
import logging
import random

import numpy as np
from sklearn.exceptions import ConvergenceWarning
import warnings

from learning.fed_cnn import FedCNN
from utils.exception_decorator import log_exceptions
from metrics.node_metrics import metrics, MetricField

import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.nn.utils import parameters_to_vector, vector_to_parameters

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
            batches = list(self._val_loader)
            selected_batches = random.sample(batches, 30)
            for Xb, yb in selected_batches:

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
    def aggregate(self, model_chunks):
        flat = self._flatten_state_dict()

        logging.info(f"Starting aggregation of {len(model_chunks)} model chunks...")

        part_hits = np.zeros_like(flat, dtype=np.int32)

        local_model_flat = self._flatten_state_dict()
        counter = np.ones_like(flat)
        flat += local_model_flat
        counter += 1
        part_hits += 1

        for chunk in model_chunks:
            start, end = chunk["start"], chunk["end"]
            array = np.frombuffer(chunk["data"], dtype=np.float32, count=end - start)
            flat[start:end] += array
            counter[start:end] += 1
            part_hits[start:end] += 1

        self._unflatten_state_dict(flat / counter)

        nonzero_parts = part_hits > 0
        hits_per_part = part_hits[nonzero_parts]

        max_hits = hits_per_part.max() if hits_per_part.size else 0
        min_hits = hits_per_part.min() if hits_per_part.size else 0
        avg_hits = hits_per_part.mean() if hits_per_part.size else 0

        logging.info(f"  Max fragments received for a part: {max_hits}")
        logging.info(f"  Min fragments received for a part: {min_hits}")
        logging.info(f"  Avg fragments per part: {avg_hits:.2f}")

    def _flatten_state_dict(self):
        return (parameters_to_vector(self._model.parameters())
                .detach().cpu().numpy().astype(np.float32))

    def _unflatten_state_dict(self, flat):
        vector_to_parameters(torch.from_numpy(flat)
                             .to(self._device), self._model.parameters())
        return self._model.state_dict()

    @log_exceptions
    def create_chunks(self, bytes_per_chunk=600):
        data = self._flatten_state_dict()
        float32_size = 4
        chunk_len = bytes_per_chunk // float32_size
        chunks = []

        for start in range(0, len(data), chunk_len):
            end = min(start + chunk_len, len(data))
            chunk = {
                "start": start,
                "end": end,
                "data": data[start:end].astype(np.float32).tobytes()
            }
            chunks.append(chunk)

        return chunks

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

