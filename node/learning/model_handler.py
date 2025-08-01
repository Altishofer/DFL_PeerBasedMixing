import asyncio
import logging
import os
import random
import warnings

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.exceptions import ConvergenceWarning
from torch.nn.utils import parameters_to_vector, vector_to_parameters
from torchvision import datasets, transforms

from learning.fed_cnn import FedCNN
from utils.config_store import ConfigStore
from utils.exception_decorator import log_exceptions
from utils.logging_config import log_header

os.environ['TORCH_CPP_LOG_LEVEL'] = 'WARNING'
warnings.filterwarnings("ignore", category=ConvergenceWarning)


class ModelHandler:

    def __init__(self, node_id, total_peers):
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model = FedCNN().to(self._device)
        self._loss_fn = nn.CrossEntropyLoss()
        self._optimizer = optim.Adam(self._model.parameters(), lr=1e-3, weight_decay=1e-4)
        self._n_train_batches = 0
        self._n_val_batches = 0
        self._train_loader, self._val_loader = self._load_partition(node_id, total_peers)

    @log_exceptions
    async def train(self):
        def train_batches():
            n_batches = min(ConfigStore.n_batches_per_round, self._n_train_batches)
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
        return round(accuracy, 3)

    @log_exceptions
    def set_model(self, model):
        self._model.load_state_dict(model)

    @log_exceptions
    def get_model(self):
        return self._model.state_dict()

    def aggregate(self, model_chunks):
        local = self._flatten_state_dict()
        flat = np.zeros_like(local, dtype=np.float32)
        counter = np.zeros_like(local, dtype=np.int32)

        flat += local
        counter += 1

        part_hits = np.zeros_like(local, dtype=np.int32)

        for chunk in model_chunks:
            start, end = chunk["start"], chunk["end"]
            array = np.frombuffer(chunk["data"], dtype=np.float32, count=end - start)
            flat[start:end] += array
            counter[start:end] += 1
            part_hits[start:end] += 1

        np.divide(flat, counter, out=flat, casting="unsafe")
        self._unflatten_state_dict(flat)

        nonzero_parts = part_hits > 0
        hits_per_part = part_hits[nonzero_parts]
        logging.info(f"Max fragments received for a part: {hits_per_part.max() if hits_per_part.size else 0}")
        logging.info(f"Min fragments received for a part: {hits_per_part.min() if hits_per_part.size else 0}")
        logging.info(
            f"Avg fragments per part: {hits_per_part.mean():.2f}" if hits_per_part.size else "Avg fragments per part: 0.00")

    def _flatten_state_dict(self):
        flat_tensors = []
        for tensor in self._model.state_dict().values():
            flat_tensors.append(tensor.detach().cpu().view(-1).to(torch.float32))
        return torch.cat(flat_tensors).numpy()

    def _unflatten_state_dict(self, flat):
        flat = torch.from_numpy(flat)
        new_state = {}
        offset = 0
        for key, tensor in self._model.state_dict().items():
            numel = tensor.numel()
            new_state[key] = flat[offset:offset + numel].view(tensor.shape).type_as(tensor)
            offset += numel
        self._model.load_state_dict(new_state)
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

        global_seed = 42
        torch.manual_seed(global_seed)
        np.random.seed(global_seed)

        train_transform = transforms.Compose([
            transforms.RandomRotation(10),
            transforms.RandomCrop(28, padding=4),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5], std=[0.5]),
        ])

        val_transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5], std=[0.5]),
        ])

        train_dataset = datasets.MNIST(
            root="/tmp/mnist",
            train=True,
            transform=train_transform,
            download=True
        )

        val_dataset = datasets.MNIST(
            root="/tmp/mnist",
            train=False,
            transform=val_transform,
            download=True
        )

        targets = train_dataset.targets.detach().clone()
        indices_by_class = {int(c): (targets == c).nonzero(as_tuple=True)[0] for c in range(10)}

        logging.info(f"Dirichlet alpha = {ConfigStore.dirichlet_alpha}")
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

        train_subset = torch.utils.data.Subset(train_dataset, node_indices.tolist())

        train_loader = torch.utils.data.DataLoader(
            dataset=train_subset,
            batch_size=ConfigStore.batch_size,
            shuffle=True,
            num_workers=0
        )

        val_loader = torch.utils.data.DataLoader(
            dataset=val_dataset,
            batch_size=ConfigStore.batch_size,
            shuffle=False,
            num_workers=0
        )

        self._n_train_batches = len(train_loader)
        self._n_val_batches = len(val_loader)

        logging.info(f"Batch Size: {ConfigStore.batch_size}")
        logging.info(f"Validation Batches: {self._n_val_batches}")
        logging.info(f"Training Batches {self._n_train_batches}")

        return train_loader, val_loader
