import requests
import numpy as np
import hashlib
import json
from web3 import Web3
from eth_utils import to_checksum_address
from backend.common.dataset_utils import load_dataset_scaled, DEFAULT_DATASET_PATH
abi = [
    {
      "inputs": [],
      "stateMutability": "nonpayable",
      "type": "constructor"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": False,
          "internalType": "address",
          "name": "client",
          "type": "address"
        }
      ],
      "name": "Blacklisted",
      "type": "event"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": False,
          "internalType": "address",
          "name": "client",
          "type": "address"
        }
      ],
      "name": "ClientRegistered",
      "type": "event"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": False,
          "internalType": "address",
          "name": "client",
          "type": "address"
        },
        {
          "indexed": False,
          "internalType": "uint256",
          "name": "round",
          "type": "uint256"
        },
        {
          "indexed": False,
          "internalType": "bytes32",
          "name": "hash",
          "type": "bytes32"
        }
      ],
      "name": "HashSubmitted",
      "type": "event"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": False,
          "internalType": "address",
          "name": "client",
          "type": "address"
        },
        {
          "indexed": False,
          "internalType": "uint256",
          "name": "newTrust",
          "type": "uint256"
        }
      ],
      "name": "TrustUpdated",
      "type": "event"
    },
    {
      "inputs": [],
      "name": "INITIAL_TRUST",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "PENALTY",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "THRESHOLD",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "name": "blacklisted",
      "outputs": [
        {
          "internalType": "bool",
          "name": "",
          "type": "bool"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "client",
          "type": "address"
        }
      ],
      "name": "getTrust",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "owner",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "client",
          "type": "address"
        }
      ],
      "name": "penalizeClient",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "registerClient",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "round",
          "type": "uint256"
        },
        {
          "internalType": "bytes32",
          "name": "hash",
          "type": "bytes32"
        }
      ],
      "name": "submitHash",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "name": "trustScore",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        },
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "name": "updateHashes",
      "outputs": [
        {
          "internalType": "bytes32",
          "name": "",
          "type": "bytes32"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "client",
          "type": "address"
        }
      ],
      "name": "rewardClient",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "REWARD",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "MAX_TRUST",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": False,
          "internalType": "address",
          "name": "client",
          "type": "address"
        },
        {
          "indexed": False,
          "internalType": "uint256",
          "name": "newTrust",
          "type": "uint256"
        }
      ],
      "name": "ClientRewarded",
      "type": "event"
    }
  ]
SERVER_URL = "http://127.0.0.1:8000"
GANACHE_URL = "http://127.0.0.1:7545"
CONTRACT_ADDRESS = "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0"

class FederatedClient:

    def __init__(self, client_id, account_index):
        self.client_id = client_id
        self.account_index = account_index

        # Blockchain setup
        self.w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
        self.account = self.w3.eth.accounts[account_index]
        self.w3.eth.default_account = self.account

        self.contract = self.w3.eth.contract(
            address=to_checksum_address(CONTRACT_ADDRESS),
            abi=abi
        )

        # Cache dataset load per-process (each client script runs once per round).
        self._dataset_cache = None

    def _ensure_dataset_loaded(self):
        if self._dataset_cache is not None:
            return self._dataset_cache

        X_scaled, y, feature_cols, label_col, mean, std = load_dataset_scaled(DEFAULT_DATASET_PATH)
        self._dataset_cache = {
            "X_scaled": X_scaled,
            "y": y,
            "feature_cols": feature_cols,
            "label_col": label_col,
            "mean": mean,
            "std": std,
        }
        return self._dataset_cache

    @staticmethod
    def _sigmoid(z: np.ndarray) -> np.ndarray:
        # Numerically stable sigmoid
        out = np.empty_like(z, dtype=float)
        pos = z >= 0
        out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
        exp_z = np.exp(z[~pos])
        out[~pos] = exp_z / (1.0 + exp_z)
        return out

    @staticmethod
    def _relu(z: np.ndarray) -> np.ndarray:
        return np.maximum(0.0, z)

    @staticmethod
    def _relu_grad(z: np.ndarray) -> np.ndarray:
        return (z > 0).astype(float)

    @staticmethod
    def _mlp_dims(input_dim: int, hidden: int = 32):
        """Return total parameter count for a 2-layer MLP: input->hidden->1."""
        # W1: input*hidden, b1: hidden, W2: hidden*1, b2: 1
        return input_dim * hidden + hidden + hidden + 1

    def _pack_mlp(self, W1, b1, W2, b2):
        return np.concatenate([W1.ravel(), b1.ravel(), W2.ravel(), b2.ravel()])

    def _unpack_mlp(self, w_flat, input_dim, hidden=32):
        idx = 0
        W1 = w_flat[idx:idx + input_dim * hidden].reshape(input_dim, hidden)
        idx += input_dim * hidden
        b1 = w_flat[idx:idx + hidden]
        idx += hidden
        W2 = w_flat[idx:idx + hidden].reshape(hidden, 1)
        idx += hidden
        b2 = w_flat[idx:idx + 1]
        return W1, b1, W2, b2

    def _train_mlp_gd(
        self,
        X: np.ndarray,
        y: np.ndarray,
        w_init: np.ndarray,
        lr: float = 0.05,
        epochs: int = 40,
        reg_lambda: float = 0.001,
        hidden: int = 32,
    ) -> np.ndarray:
        """
        2-layer MLP (input->ReLU->hidden->sigmoid->1) trained with mini-batch GD.
        All weights packed into a single flat vector for FL compatibility.
        """
        n, d = X.shape
        W1, b1, W2, b2 = self._unpack_mlp(w_init, d, hidden)

        batch_size = min(128, n)
        rng = np.random.default_rng(42)

        for epoch in range(epochs):
            perm = rng.permutation(n)
            for start in range(0, n, batch_size):
                batch_idx = perm[start:start + batch_size]
                Xb = X[batch_idx]
                yb = y[batch_idx].reshape(-1, 1)
                bs = Xb.shape[0]

                # Forward
                z1 = Xb @ W1 + b1          # (bs, hidden)
                a1 = self._relu(z1)         # (bs, hidden)
                z2 = a1 @ W2 + b2           # (bs, 1)
                a2 = self._sigmoid(z2)      # (bs, 1)

                # Backward
                dz2 = (a2 - yb) / bs        # (bs, 1)
                dW2 = a1.T @ dz2            # (hidden, 1)
                db2 = np.sum(dz2, axis=0)   # (1,)

                da1 = dz2 @ W2.T            # (bs, hidden)
                dz1 = da1 * self._relu_grad(z1)  # (bs, hidden)
                dW1 = Xb.T @ dz1            # (d, hidden)
                db1 = np.sum(dz1, axis=0)   # (hidden,)

                # L2 regularization
                dW1 += reg_lambda * W1
                dW2 += reg_lambda * W2

                W1 -= lr * dW1
                b1 -= lr * db1
                W2 -= lr * dW2
                b2 -= lr * db2

        return self._pack_mlp(W1, b1, W2, b2)

    def _train_logreg_gd(
        self,
        X: np.ndarray,
        y: np.ndarray,
        w_init: np.ndarray,
        lr: float = 0.3,
        epochs: int = 60,
        reg_lambda: float = 0.01,
    ) -> np.ndarray:
        """
        Logistic regression trained with gradient descent (legacy fallback).
        w includes bias as the last component.
        """
        n, d = X.shape
        X_aug = np.concatenate([X, np.ones((n, 1), dtype=float)], axis=1)
        w = w_init.astype(float).copy()

        if w.shape[0] != X_aug.shape[1]:
            raise ValueError(f"Weight dim mismatch: w={w.shape[0]} vs X_aug={X_aug.shape[1]}")

        for _ in range(epochs):
            z = X_aug @ w
            p = self._sigmoid(z)
            grad = (X_aug.T @ (p - y)) / n
            grad[:-1] += reg_lambda * w[:-1]
            w = w - lr * grad

        return w

    @staticmethod
    def _dirichlet_partition(n_samples: int, n_clients: int, alpha: float = 0.5, seed: int = 42):
        """
        Non-IID Dirichlet partitioning: allocate sample indices to clients
        using a Dirichlet distribution. Lower alpha = more heterogeneous.
        """
        rng = np.random.default_rng(seed)
        proportions = rng.dirichlet(np.repeat(alpha, n_clients))
        # Convert proportions to actual index counts
        counts = (proportions * n_samples).astype(int)
        # Fix rounding: give remainders to random clients
        remainder = n_samples - counts.sum()
        for i in range(abs(remainder)):
            counts[i % n_clients] += 1 if remainder > 0 else -1
        counts = np.maximum(counts, 1)  # ensure at least 1 sample per client

        indices = rng.permutation(n_samples)
        partitions = []
        start = 0
        for c in counts:
            end = min(start + c, n_samples)
            partitions.append(indices[start:end])
            start = end
        return partitions

    def register(self):
        try:
            self.contract.functions.registerClient().transact()
            print(f"{self.client_id} registered on blockchain")
        except:
            print(f"{self.client_id} already registered")

    def get_global_model(self):
        response = requests.get(f"{SERVER_URL}/get_global_model")
        data = response.json()
        return np.array(data["weights"]), data["round"]

    def train(self, global_weights, round_number: int, label_flip_ratio: float = 0.0):
        """
        Train local fraud detector using 2-layer MLP on non-IID Dirichlet partition.
        Falls back to logistic regression if weight dimensions indicate legacy model.
        """
        try:
            ds = self._ensure_dataset_loaded()
        except Exception:
            # If dataset isn't available, keep the demo behavior:
            if label_flip_ratio > 0:
                scale = 1.0 + (10.0 * float(label_flip_ratio))
            else:
                scale = 0.1
            return global_weights + np.random.normal(0, scale, size=global_weights.shape)

        X_scaled = ds["X_scaled"]
        y = ds["y"]
        input_dim = X_scaled.shape[1]

        # Non-IID Dirichlet partitioning (alpha=0.5 for realistic heterogeneity)
        participants = 4
        client_part = (self.account_index - 1) % participants
        partitions = self._dirichlet_partition(
            X_scaled.shape[0], participants, alpha=0.5, seed=42
        )
        part_idx = partitions[client_part]

        X_part = X_scaled[part_idx]
        y_part = y[part_idx].copy()

        # Malicious behavior: label flipping.
        if label_flip_ratio > 0:
            rng = np.random.default_rng(seed=round_number + client_part * 1000)
            flip_mask = rng.random(size=y_part.shape[0]) < label_flip_ratio
            y_part = np.where(flip_mask, 1.0 - y_part, y_part)

        # Detect model type by weight dimension
        expected_mlp_dim = self._mlp_dims(input_dim, hidden=32)
        expected_logreg_dim = input_dim + 1

        if global_weights.shape[0] == expected_mlp_dim:
            # MLP training
            return self._train_mlp_gd(
                X_part, y_part, w_init=global_weights,
                lr=0.05, epochs=40, reg_lambda=0.001, hidden=32,
            )
        else:
            # Legacy logistic regression fallback
            return self._train_logreg_gd(X_part, y_part, w_init=global_weights)

    def submit_update(self, weights, round_number):
        # Hash weights using the same canonical JSON representation
        # so the server can verify on-chain commitment byte-for-byte.
        weights_list = np.round(np.array(weights, dtype=float), 6).tolist()
        hash_input = json.dumps(weights_list, separators=(",", ":"))
        hash_hex = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        hash_bytes32 = bytes.fromhex(hash_hex)

        # Submit hash to blockchain
        try:
            self.contract.functions.submitHash(round_number, hash_bytes32).transact()
        except Exception as e:
            print("Blockchain rejected transaction:", e)
            # Even if hash submission fails (e.g., already blacklisted), still
            # forward the weights to the server. The server will compare
            # against the on-chain committed hash and penalize accordingly.

        # Send weights to server
        payload = {
            "client_id": self.client_id,
            "client_address": self.account,
            "round_number": round_number,
            "weights": weights_list,
        }

        response = requests.post(f"{SERVER_URL}/submit_update", json=payload)
        print(response.json())