import asyncio
import logging
import random

import numpy as np
from sklearn.exceptions import ConvergenceWarning
import warnings

from learning.fed_cnn import FedCNN
from utils.exception_decorator import log_exceptions
from utils.logging_config import log_header

import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.nn.utils import parameters_to_vector, vector_to_parameters
from utils.config_store import ConfigStore

import os
os.environ['TORCH_CPP_LOG_LEVEL'] = 'WARNING'
warnings.filterwarnings("ignore", category=ConvergenceWarning)


class ModelHandler:

    ConfigStore.batch_size = 64
    ConfigStore.dirichlet_alpha = 10
    ConfigStore.n_batches_per_round = 5

    def __init__(self, node_id, total_peers):
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model = FedCNN().to(self._device)
        self._loss_fn = nn.CrossEntropyLoss()
        self._optimizer = optim.Adam(self._model.parameters(), lr=1e-3)
        self._n_train_batches = 0
        self._n_val_batches = 0
        self._train_loader, self._val_loader = self._load_partition(node_id, total_peers)

    @log_exceptions
    async def train(self):
        def train_batches():
            n_batches = ConfigStore.n_batches_per_round
            logging.info(f"Training on {n_batches} of {self._n_train_batches} batches")
            self._model.train()
            batches = list(self._train_loader)
            random_batches = random.sample(batches, n_batches)
            for Xb, yb in random_batches:
                Xb, yb = Xb.to(self._device), yb.to(self._device)
                self._optimizer.zero_grad()
                loss = self._loss_fn(self._model(Xb), yb)
                loss.backward()
                self._optimizer.step()

        await asyncio.to_thread(train_batches)

    @log_exceptions
    async def evaluate(self):
        logging.info(f"Validating on {len(self._val_loader)} batches")
        self._model.eval()

        def evaluate_batches():
            correct = total = 0
            with torch.no_grad():
                for Xb, yb in self._val_loader:
                    Xb, yb = Xb.to(self._device), yb.to(self._device)
                    pred = self._model(Xb)
                    correct += (pred.argmax(1) == yb).sum().item()
                    total += yb.size(0)
            return correct / total

        accuracy = await asyncio.to_thread(evaluate_batches)
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

        part_hits = np.zeros_like(flat, dtype=np.int32)
        counter = np.ones_like(flat)

        # Add local model to the aggregation
        local_model_flat = self._flatten_state_dict()
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

        logging.info(f"Max fragments received for a part: {max_hits}")
        logging.info(f"Min fragments received for a part: {min_hits}")
        logging.info(f"Avg fragments per part: {avg_hits:.2f}")

    def _flatten_state_dict(self):
        return (parameters_to_vector(self._model.parameters())
                .detach().cpu().numpy().astype(np.float32))

    def _unflatten_state_dict(self, flat):
        vector_to_parameters(torch.from_numpy(flat)
                             .to(self._device), self._model.parameters())
        return self._model.state_dict()

    @log_exceptions
    def create_chunks(self, bytes_per_chunk=512):
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

    def _load_partition(self, node_id, total_peers):
        log_header("Dataset")

        torch.manual_seed(42)

        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,))
        ])

        dataset = datasets.MNIST(root="/tmp/mnist", train=True, transform=transform, download=True)
        val_dataset = datasets.MNIST(root="/tmp/mnist", train=False, transform=transform, download=True)

        targets = dataset.targets.detach().clone()
        indices_by_class = {int(c): (targets == c).nonzero(as_tuple=True)[0] for c in range(10)}

        logging.info(f"Using a Dirichlet distribution with alpha = {ConfigStore.dirichlet_alpha}")
        alpha = torch.full((total_peers,), float(ConfigStore.dirichlet_alpha), dtype=torch.float32)
        dirichlet = torch.distributions.Dirichlet(alpha)

        node_indices = []

        for cls, class_indices in indices_by_class.items():
            class_indices = class_indices[torch.randperm(class_indices.size(0))]
            proportions = dirichlet.sample()
            counts = torch.floor(proportions * len(class_indices)).long()
            counts[-1] = len(class_indices) - counts[:-1].sum()

            start = 0
            for peer_id, count in enumerate(counts):
                end = start + count.item()
                if peer_id == node_id:
                    node_indices.append(class_indices[start:end])
                start = end

        node_indices = torch.cat(node_indices)
        node_indices = node_indices[torch.randperm(node_indices.size(0))]

        train_subset = torch.utils.data.Subset(dataset, node_indices.tolist())

        val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=ConfigStore.batch_size, shuffle=False)
        train_loader = torch.utils.data.DataLoader(train_subset, batch_size=ConfigStore.batch_size, shuffle=True)

        self._n_train_batches = len(train_loader)
        self._n_val_batches = len(val_loader)

        logging.info(f"Batch Size: {ConfigStore.batch_size}")
        logging.info(f"Validation Batches: {self._n_val_batches}")
        logging.info(f"Training Batches {self._n_train_batches}")

        return train_loader, val_loader
