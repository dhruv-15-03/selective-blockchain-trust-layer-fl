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
    }
  ]
SERVER_URL = "http://127.0.0.1:8000"
GANACHE_URL = "http://127.0.0.1:7545"
CONTRACT_ADDRESS = "0xf58D411D133F0Cd384421FC717B443BDc00A6DD5"

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
        Logistic regression trained with gradient descent, no external ML libs.
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

            # L2 regularization on coefficients only (exclude bias)
            grad[:-1] += reg_lambda * w[:-1]
            w = w - lr * grad

        return w

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
        Train local fraud detector.
        - If dataset exists: train logistic regression on this client's partition.
        - If dataset missing: keep synthetic demo behavior.
        """
        try:
            ds = self._ensure_dataset_loaded()
        except Exception:
            # If dataset isn't available, keep the demo behavior:
            # - honest: small random deviation
            # - malicious (label_flip_ratio > 0): large random deviation
            if label_flip_ratio > 0:
                scale = 1.0 + (10.0 * float(label_flip_ratio))
            else:
                scale = 0.1
            return global_weights + np.random.normal(0, scale, size=global_weights.shape)

        X_scaled = ds["X_scaled"]
        y = ds["y"]

        # Deterministic partition: 4 participants demo.
        participants = 4
        client_part = (self.account_index - 1) % participants

        idx = np.arange(X_scaled.shape[0])
        mask = (idx % participants) == client_part
        X_part = X_scaled[mask]
        y_part = y[mask].copy()

        # Malicious behavior: label flipping.
        if label_flip_ratio > 0:
            rng = np.random.default_rng(seed=round_number + client_part * 1000)
            flip_mask = rng.random(size=y_part.shape[0]) < label_flip_ratio
            y_part = np.where(flip_mask, 1.0 - y_part, y_part)

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