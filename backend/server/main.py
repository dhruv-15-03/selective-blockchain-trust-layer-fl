from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sys
from pathlib import Path
from typing import List
import numpy as np
from blockchain_interface import contract, w3
import hashlib
import json
from eth_utils import to_checksum_address
import time
from typing import Dict, Any, Optional, List, Tuple
import math

# Ensure repo root is on sys.path so `backend.*` imports work when running uvicorn from `backend/server`.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.common.dataset_utils import infer_dataset_schema, load_dataset_scaled, DEFAULT_DATASET_PATH

# Auth (optional - requires: pip install sqlalchemy psycopg2-binary passlib python-jose)
try:
    from auth_routes import router as auth_router
    from database import init_db as _init_db
    _AUTH_AVAILABLE = True
except ImportError as e:
    _AUTH_AVAILABLE = False
    auth_router = None
    _init_db = None

# Feature routes (profile, subscriptions, jobs, GitHub analysis)
try:
    from feature_routes import router as feature_router
    _FEATURES_AVAILABLE = True
except ImportError:
    _FEATURES_AVAILABLE = False
    feature_router = None

app = FastAPI()

if _AUTH_AVAILABLE and auth_router:
    app.include_router(auth_router)
if _FEATURES_AVAILABLE and feature_router:
    app.include_router(feature_router)

# CORS for React dev server (port 5173) and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model (initialized; may be overwritten on startup if dataset exists)
global_model = np.array([0.5, 0.5, 0.5], dtype=float)

# Fraud classifier weights used for Upwork-style AI risk scoring.
fraud_model_weights: Optional[np.ndarray] = None  # includes bias term as last element
fraud_feature_dim: int = 0
fraud_accept_threshold: float = 0.6

# Dataset normalization params (set at startup if dataset exists)
_dataset_mean: Optional[np.ndarray] = None
_dataset_std: Optional[np.ndarray] = None
_dataset_feature_cols: Optional[List[str]] = None

# Model evaluation metrics (computed at startup & after each aggregation)
model_metrics: Dict[str, Any] = {}

# Held-out test set for evaluation (set at startup)
_X_test: Optional[np.ndarray] = None
_y_test: Optional[np.ndarray] = None

current_round = 1
expected_clients = 3 
client_updates = {} 
submitted_clients = set()
trust_history = {}
client_address_mapping = {}

class MahalanobisAnomalyDetector:
    """
    Statistical anomaly detector trained on "honest deviations".
    Uses Mahalanobis distance + cosine similarity as dual signals.
    """

    def __init__(self, threshold_percentile: float = 0.995, epsilon: float = 1e-6):
        self.threshold_percentile = threshold_percentile
        self.epsilon = epsilon
        self.mean = None
        self.cov_inv = None
        self.threshold = None
        self.cosine_threshold = None  # minimum cosine similarity to honest mean

    def fit(self, X: np.ndarray) -> None:
        # X: (n_samples, n_features)
        self.mean = np.mean(X, axis=0)
        cov = np.cov(X.T, bias=True)
        cov = cov + self.epsilon * np.eye(cov.shape[0])
        self.cov_inv = np.linalg.inv(cov)

        md2_scores = self.score_samples(X)
        self.threshold = float(np.quantile(md2_scores, self.threshold_percentile))

        # Cosine similarity threshold: 1st percentile of training data
        cos_scores = self._cosine_scores(X)
        self.cosine_threshold = float(np.quantile(cos_scores, 1.0 - self.threshold_percentile))

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        diffs = X - self.mean
        left = diffs @ self.cov_inv
        md2 = np.sum(left * diffs, axis=1)
        return md2

    def _cosine_scores(self, X: np.ndarray) -> np.ndarray:
        mean_norm = np.linalg.norm(self.mean)
        if mean_norm < 1e-12:
            return np.ones(X.shape[0])
        scores = np.array([
            float(np.dot(x, self.mean) / (np.linalg.norm(x) * mean_norm + 1e-12))
            for x in X
        ])
        return scores

    def predict_one(self, x: np.ndarray) -> tuple[bool, float]:
        x2 = x.reshape(1, -1)
        md2 = float(self.score_samples(x2)[0])
        md2_flag = md2 > self.threshold

        # Cosine similarity check (catches directional poisoning)
        cos_sim = float(np.dot(x, self.mean) / (np.linalg.norm(x) * np.linalg.norm(self.mean) + 1e-12))
        cos_flag = self.cosine_threshold is not None and cos_sim < self.cosine_threshold

        return md2_flag or cos_flag, md2


def _evaluate_model(weights: np.ndarray, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
    """Evaluate a model (MLP or logistic regression) on test data."""
    n = X_test.shape[0]
    if n == 0:
        return {}
    input_dim = X_test.shape[1]
    HIDDEN = 32
    expected_mlp_dim = input_dim * HIDDEN + HIDDEN + HIDDEN + 1
    expected_logreg_dim = input_dim + 1

    if weights.shape[0] == expected_mlp_dim:
        # MLP forward pass
        idx = 0
        W1 = weights[idx:idx + input_dim * HIDDEN].reshape(input_dim, HIDDEN)
        idx += input_dim * HIDDEN
        b1 = weights[idx:idx + HIDDEN]
        idx += HIDDEN
        W2 = weights[idx:idx + HIDDEN].reshape(HIDDEN, 1)
        idx += HIDDEN
        b2 = weights[idx:idx + 1]
        z1 = X_test @ W1 + b1
        a1 = np.maximum(0.0, z1)  # ReLU
        z2 = a1 @ W2 + b2
        probs = np.where(z2 >= 0, 1.0 / (1.0 + np.exp(-z2)), np.exp(z2) / (1.0 + np.exp(z2)))
        probs = probs.ravel()
    else:
        # Logistic regression fallback
        X_aug = np.concatenate([X_test, np.ones((n, 1), dtype=float)], axis=1)
        z = X_aug @ weights
        probs = np.where(z >= 0, 1.0 / (1.0 + np.exp(-z)), np.exp(z) / (1.0 + np.exp(z)))

    preds = (probs >= 0.5).astype(float)

    tp = float(np.sum((preds == 1) & (y_test == 1)))
    tn = float(np.sum((preds == 0) & (y_test == 0)))
    fp = float(np.sum((preds == 1) & (y_test == 0)))
    fn = float(np.sum((preds == 0) & (y_test == 1)))

    accuracy = (tp + tn) / n
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # AUC (trapezoidal, sorted by probability)
    sorted_idx = np.argsort(-probs)
    sorted_y = y_test[sorted_idx]
    n_pos = float(np.sum(y_test == 1))
    n_neg = float(n - n_pos)
    auc = 0.0
    if n_pos > 0 and n_neg > 0:
        tp_rate = 0.0
        fp_rate = 0.0
        prev_tp_rate = 0.0
        prev_fp_rate = 0.0
        for label in sorted_y:
            if label == 1:
                tp_rate += 1.0 / n_pos
            else:
                fp_rate += 1.0 / n_neg
            auc += 0.5 * (tp_rate + prev_tp_rate) * (fp_rate - prev_fp_rate)
            prev_tp_rate = tp_rate
            prev_fp_rate = fp_rate

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "auc": round(auc, 4),
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
        "test_samples": n,
    }


anomaly_detector = MahalanobisAnomalyDetector()


@app.on_event("startup")
def _startup():
    if _AUTH_AVAILABLE and _init_db:
        try:
            import models  # noqa: F401 - register tables
            _init_db()
            print("Auth DB initialized")
        except Exception as e:
            print("Auth DB init skipped:", e)
    _startup_train_anomaly_detector()


def _startup_train_anomaly_detector():
    global global_model, fraud_model_weights, fraud_feature_dim
    global model_metrics, _dataset_mean, _dataset_std, _dataset_feature_cols
    global _X_test, _y_test

    # If dataset exists, train the anomaly detector on *realistic* honest
    # logistic-regression weight vectors generated from the dataset.
    try:
        X_scaled, y, feature_cols, label_col, mean, std = load_dataset_scaled(DEFAULT_DATASET_PATH)

        # Store normalization params for Upwork feature extraction
        _dataset_mean = mean
        _dataset_std = std
        _dataset_feature_cols = feature_cols

        # ---- Train/Test Split (80/20, stratified) ----
        n_total = X_scaled.shape[0]
        rng_split = np.random.default_rng(99)
        pos_idx = np.where(y == 1)[0]
        neg_idx = np.where(y == 0)[0]
        rng_split.shuffle(pos_idx)
        rng_split.shuffle(neg_idx)
        n_pos_test = max(1, int(len(pos_idx) * 0.2))
        n_neg_test = max(1, int(len(neg_idx) * 0.2))
        test_idx = np.concatenate([pos_idx[:n_pos_test], neg_idx[:n_neg_test]])
        train_idx = np.concatenate([pos_idx[n_pos_test:], neg_idx[n_neg_test:]])
        rng_split.shuffle(train_idx)

        X_train_data = X_scaled[train_idx]
        y_train_data = y[train_idx]
        _X_test = X_scaled[test_idx]
        _y_test = y[test_idx]

        participants = 4
        print(
            f"Dataset detected: label={label_col}, features={len(feature_cols)}. "
            f"Train={len(train_idx)}, Test={len(test_idx)}. Training MLP + anomaly gate..."
        )

        def sigmoid(z: np.ndarray) -> np.ndarray:
            out = np.empty_like(z, dtype=float)
            pos = z >= 0
            out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
            exp_z = np.exp(z[~pos])
            out[~pos] = exp_z / (1.0 + exp_z)
            return out

        def relu(z: np.ndarray) -> np.ndarray:
            return np.maximum(0.0, z)

        def relu_grad(z: np.ndarray) -> np.ndarray:
            return (z > 0).astype(float)

        HIDDEN = 32

        def mlp_dims(input_dim: int, hidden: int = HIDDEN) -> int:
            return input_dim * hidden + hidden + hidden + 1

        def pack_mlp(W1, b1, W2, b2):
            return np.concatenate([W1.ravel(), b1.ravel(), W2.ravel(), b2.ravel()])

        def unpack_mlp(w_flat, input_dim, hidden=HIDDEN):
            idx = 0
            W1 = w_flat[idx:idx + input_dim * hidden].reshape(input_dim, hidden)
            idx += input_dim * hidden
            b1 = w_flat[idx:idx + hidden]
            idx += hidden
            W2 = w_flat[idx:idx + hidden].reshape(hidden, 1)
            idx += hidden
            b2 = w_flat[idx:idx + 1]
            return W1, b1, W2, b2

        def train_mlp_gd(X_part, y_part, w_init, lr=0.05, epochs=40, reg_lambda=0.001, hidden=HIDDEN):
            n, d = X_part.shape
            W1, b1, W2, b2 = unpack_mlp(w_init, d, hidden)
            batch_size = min(128, n)
            rng_mlp = np.random.default_rng(42)
            for _ in range(epochs):
                perm = rng_mlp.permutation(n)
                for start in range(0, n, batch_size):
                    bi = perm[start:start + batch_size]
                    Xb = X_part[bi]
                    yb = y_part[bi].reshape(-1, 1)
                    bs = Xb.shape[0]
                    z1 = Xb @ W1 + b1
                    a1 = relu(z1)
                    z2 = a1 @ W2 + b2
                    a2 = sigmoid(z2)
                    dz2 = (a2 - yb) / bs
                    dW2 = a1.T @ dz2
                    db2 = np.sum(dz2, axis=0)
                    da1 = dz2 @ W2.T
                    dz1 = da1 * relu_grad(z1)
                    dW1 = Xb.T @ dz1
                    db1 = np.sum(dz1, axis=0)
                    dW1 += reg_lambda * W1
                    dW2 += reg_lambda * W2
                    W1 -= lr * dW1
                    b1 -= lr * db1
                    W2 -= lr * dW2
                    b2 -= lr * db2
            return pack_mlp(W1, b1, W2, b2)

        def dirichlet_partition(n_samples, n_clients, alpha=0.5, seed=42):
            rng_d = np.random.default_rng(seed)
            proportions = rng_d.dirichlet(np.repeat(alpha, n_clients))
            counts = (proportions * n_samples).astype(int)
            counts = np.maximum(counts, 1)
            remainder = n_samples - counts.sum()
            for i in range(abs(remainder)):
                counts[i % n_clients] += 1 if remainder > 0 else -1
            indices = rng_d.permutation(n_samples)
            partitions = []
            start = 0
            for c in counts:
                partitions.append(indices[start:start + c])
                start += c
            return partitions

        input_dim = int(X_scaled.shape[1])
        mlp_total_params = mlp_dims(input_dim, HIDDEN)
        dim = mlp_total_params
        # Initialize MLP weights (Xavier init)
        rng_init = np.random.default_rng(7)
        W1_init = rng_init.normal(0, np.sqrt(2.0 / input_dim), (input_dim, HIDDEN))
        b1_init = np.zeros(HIDDEN)
        W2_init = rng_init.normal(0, np.sqrt(2.0 / HIDDEN), (HIDDEN, 1))
        b2_init = np.zeros(1)
        global_model = pack_mlp(W1_init, b1_init, W2_init, b2_init)

        print(
            f"MLP model: input={input_dim}, hidden={HIDDEN}, total_params={dim}. "
            f"Training anomaly gate..."
        )

        rng = np.random.default_rng(42)
        n_gate_samples = max(300, dim // 4)  # enough for stable covariance
        sample_size = min(500, X_train_data.shape[0] // participants)

        weights_samples: List[np.ndarray] = []
        for i in range(n_gate_samples):
            client_part = i % participants
            # Use Dirichlet partitioning for non-IID gate training
            parts = dirichlet_partition(X_train_data.shape[0], participants, alpha=0.5, seed=42)
            part_idx = parts[client_part]
            if len(part_idx) == 0:
                continue
            chosen = rng.choice(part_idx, size=min(sample_size, len(part_idx)), replace=False)
            X_part = X_train_data[chosen]
            y_part = y_train_data[chosen]
            w = train_mlp_gd(X_part, y_part, w_init=global_model, lr=0.05, epochs=15, reg_lambda=0.001)
            weights_samples.append(w)

        X_gate_train = np.vstack(weights_samples) if weights_samples else np.zeros((1, dim))
        anomaly_detector.fit(X_gate_train)
        print(
            f"ML anomaly detector trained (MLP gate): md2_threshold={anomaly_detector.threshold:.6f}, "
            f"cosine_threshold={anomaly_detector.cosine_threshold:.6f} (dim={dim}, n={X_gate_train.shape[0]})"
        )

        # Train a trust-gated global fraud model (federated MLP) on TRAIN data.
        fraud_feature_dim = input_dim
        parts = dirichlet_partition(X_train_data.shape[0], participants, alpha=0.5, seed=42)

        local_weights: List[np.ndarray] = []
        accepted_weights: List[np.ndarray] = []
        for part in range(participants):
            part_idx = parts[part]
            X_part = X_train_data[part_idx]
            y_part = y_train_data[part_idx].copy()

            # Simulate one malicious participant by label-flipping.
            if part == 3:
                rng_part = np.random.default_rng(123 + int(part))
                flip_mask = rng_part.random(size=y_part.shape[0]) < 0.35
                y_part = np.where(flip_mask, 1.0 - y_part, y_part)

            w_local = train_mlp_gd(
                X_part, y_part, w_init=global_model,
                lr=0.05, epochs=30, reg_lambda=0.001,
            )
            local_weights.append(w_local)

            deviation_vec = w_local - global_model
            is_malicious, _ = anomaly_detector.predict_one(deviation_vec)
            if not is_malicious:
                accepted_weights.append(w_local)

        if accepted_weights:
            fraud_model_weights = np.mean(np.vstack(accepted_weights), axis=0)
        else:
            fraud_model_weights = np.mean(np.vstack(local_weights), axis=0)

        # ---- Evaluate on held-out test set ----
        if _X_test is not None and _y_test is not None:
            model_metrics = _evaluate_model(fraud_model_weights, _X_test, _y_test)
            model_metrics["round"] = 0
            model_metrics["aggregation_method"] = "trust_gated_mlp_fedavg"
            model_metrics["model_type"] = "MLP"
            model_metrics["hidden_units"] = HIDDEN
            model_metrics["total_params"] = dim
            print(
                f"Initial MLP model evaluation on test set: "
                f"accuracy={model_metrics['accuracy']}, f1={model_metrics['f1']}, "
                f"auc={model_metrics['auc']}, precision={model_metrics['precision']}, "
                f"recall={model_metrics['recall']}"
            )

        print(
            f"Trust-gated MLP fraud model ready: dim={fraud_feature_dim}, params={dim} "
            f"(accepted_locals={len(accepted_weights)}/{participants})"
        )
    except Exception as e:
        # Fallback demo: train anomaly detector on synthetic "honest deviations".
        print(f"No dataset detected for ML gate; falling back to demo dim=3. Reason: {e}")
        global_model = np.array([0.5, 0.5, 0.5], dtype=float)
        np.random.seed(42)
        n = 8000
        dim = int(global_model.shape[0])
        honest_1 = np.random.normal(loc=0.0, scale=0.1, size=(int(n * 0.75), dim))
        honest_2 = np.random.normal(loc=0.0, scale=0.06, size=(int(n * 0.25), dim))
        X_train = np.vstack([honest_1, honest_2])
        anomaly_detector.fit(X_train)
        print(f"ML anomaly detector trained (fallback): md2_threshold={anomaly_detector.threshold:.6f} (dim={dim})")

        fraud_feature_dim = max(0, dim - 1)
        # Default weights for risk scoring (used only if dataset missing).
        fraud_model_weights = np.zeros(dim, dtype=float)
        fraud_model_weights[:] = 0.1

    # Register the contract owner address so the server can commit AI/decision hashes on-chain.
    # (submitHash requires trustScore[msg.sender] > 0)
    try:
        tx = contract.functions.registerClient().transact()
        w3.eth.wait_for_transaction_receipt(tx)
    except Exception:
        pass


class ModelUpdate(BaseModel):
    client_id: str
    client_address: str
    round_number: int
    weights: list

@app.get("/")
def root():
    try:
        index_path = Path(__file__).with_name("index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return {"message": "Aggregator Server is running (index.html not found)"}

@app.get("/get_global_model")
def get_global_model():
    return {
        "round": current_round,
        "weights": global_model.tolist()
    }


@app.post("/submit_update")
def submit_update(update: ModelUpdate):
    global client_updates, submitted_clients, current_round, global_model
    global trust_history, client_address_mapping

    # Enforce correct round so the server can verify the client's submitted on-chain hash.
    if update.round_number != current_round:
        return {
            "message": "Wrong round",
            "expected_round": current_round,
            "got_round": update.round_number,
        }

    # 🔹 Prevent duplicate submission in same round
    if update.client_id in submitted_clients:
        return {"message": "Already submitted for this round"}

    client_addr = to_checksum_address(update.client_address)
    weights_array = np.array(update.weights, dtype=float)
    client_address_mapping[update.client_id] = client_addr

    # 🔥 1️⃣ Hash verification from blockchain (security)
    # The received weights must match the on-chain committed hash for this round.
    weights_list = update.weights
    hash_input = json.dumps(weights_list, separators=(",", ":"))
    hash_hex = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    computed_hash_bytes32 = bytes.fromhex(hash_hex)

    onchain_hash = contract.functions.updateHashes(update.round_number, client_addr).call()
    onchain_hash_bytes = bytes(onchain_hash)
    computed_hash_bytes = bytes(computed_hash_bytes32)

    hash_is_set = onchain_hash_bytes != (b"\x00" * 32)
    hash_matches = hash_is_set and (onchain_hash_bytes == computed_hash_bytes)

    # 🔥 2️⃣ ML-based malicious detection (statistical anomaly detector)
    deviation_vec = weights_array - global_model  # feature vector (length 3)
    is_malicious_ml, md2_score = anomaly_detector.predict_one(deviation_vec)
    is_malicious = (not hash_matches) or is_malicious_ml

    if is_malicious:
        print(
            "⚠ Malicious update detected!",
            f"ml={is_malicious_ml}",
            f"hash_matches={hash_matches}",
            f"md2={md2_score:.4f}",
        )

        tx = contract.functions.penalizeClient(client_addr).transact()
        w3.eth.wait_for_transaction_receipt(tx)

        new_trust = contract.functions.getTrust(client_addr).call()
        submitted_clients.add(update.client_id)

        return {
            "message": "Client penalized (malicious update or hash mismatch)",
            "new_trust": new_trust,
            "md2_score": md2_score,
            "hash_matches": hash_matches,
        }

    # 🔥 3️⃣ Trust verification from blockchain (authorization)
    trust = contract.functions.getTrust(client_addr).call()
    threshold_contract = contract.functions.THRESHOLD().call()

    if trust < threshold_contract:
        submitted_clients.add(update.client_id)
        return {"message": "Client rejected due to low trust", "trust": trust}

    # 🔥 Store valid update
    client_updates[update.client_id] = weights_array
    submitted_clients.add(update.client_id)

    # 🔥 4️⃣ Trust recovery: reward client for a good update
    try:
        tx = contract.functions.rewardClient(client_addr).transact()
        w3.eth.wait_for_transaction_receipt(tx)
        trust = contract.functions.getTrust(client_addr).call()
    except Exception:
        pass  # reward not available on older contract deployment

    return {
        "message": "Update accepted",
        "trust": trust,
        "current_round": current_round,
        "md2_score": md2_score,
        "hash_matches": hash_matches,
        "rewarded": True,
    }

# 🔥 Aggregation endpoint — Trust-Weighted + Trimmed Mean
@app.post("/aggregate")
def aggregate():
    global global_model, current_round, fraud_model_weights, model_metrics
    global client_updates, submitted_clients
    global trust_history, client_address_mapping

    accepted_updates_count = len(client_updates)

    # 🔥 1️⃣ Trust-Weighted Robust Aggregation
    if accepted_updates_count > 0:
        client_ids = list(client_updates.keys())
        updates = [client_updates[cid] for cid in client_ids]

        # Fetch on-chain trust scores for weighting
        trust_scores = []
        for cid in client_ids:
            addr = client_address_mapping.get(cid)
            if addr:
                t = contract.functions.getTrust(addr).call()
            else:
                t = 0
            trust_scores.append(float(t))

        trust_arr = np.array(trust_scores, dtype=float)
        updates_mat = np.vstack(updates)  # (n_clients, dim)

        if accepted_updates_count >= 4:
            # Coordinate-wise Trimmed Mean (trim 10% from each end per dimension)
            trim_frac = 0.1
            trim_k = max(1, int(accepted_updates_count * trim_frac))
            trimmed = np.zeros(updates_mat.shape[1], dtype=float)
            for d in range(updates_mat.shape[1]):
                col = updates_mat[:, d]
                sorted_idx = np.argsort(col)
                keep_idx = sorted_idx[trim_k: len(sorted_idx) - trim_k]
                # Trust-weighted mean of kept values
                kept_vals = col[keep_idx]
                kept_trusts = trust_arr[keep_idx]
                total_trust = kept_trusts.sum()
                if total_trust > 0:
                    trimmed[d] = np.sum(kept_vals * kept_trusts) / total_trust
                else:
                    trimmed[d] = np.mean(kept_vals)
            global_model = trimmed
            agg_method = "trust_weighted_trimmed_mean"
        else:
            # Trust-weighted average (fewer than 4 clients — can't trim)
            total_trust = trust_arr.sum()
            if total_trust > 0:
                weights = trust_arr / total_trust
                global_model = (updates_mat.T @ weights)
            else:
                global_model = np.mean(updates_mat, axis=0)
            agg_method = "trust_weighted_avg"

        # Update fraud model weights to match aggregated global model
        fraud_model_weights = global_model.copy()

        # 🔥 Evaluate updated model on held-out test set
        if _X_test is not None and _y_test is not None:
            model_metrics = _evaluate_model(global_model, _X_test, _y_test)
            model_metrics["round"] = current_round
            model_metrics["aggregation_method"] = agg_method
            print(
                f"Round {current_round} evaluation: "
                f"accuracy={model_metrics['accuracy']}, f1={model_metrics['f1']}, "
                f"auc={model_metrics['auc']} [{agg_method}]"
            )

    # 🔥 2️⃣ Record trust for this round
    for client_id in submitted_clients:

        if client_id not in client_address_mapping:
            continue

        client_addr = client_address_mapping[client_id]
        trust = contract.functions.getTrust(client_addr).call()

        if client_id not in trust_history:
            trust_history[client_id] = []

        trust_history[client_id].append(trust)

    # 🔥 3️⃣ Prepare response
    response = {
        "message": "Aggregation complete",
        "new_global_model": global_model.tolist(),
        "next_round": current_round + 1,
        "trust_snapshot": trust_history,
        "accepted_updates_count": accepted_updates_count,
        "participants_count": len(submitted_clients),
        "model_metrics": model_metrics,
    }

    # 🔥 4️⃣ Clear round data
    client_updates.clear()
    submitted_clients.clear()

    # 🔥 5️⃣ Move to next round
    current_round += 1

    return response


@app.get("/trust_history")
def get_trust_history():
    return trust_history


@app.get("/model_metrics")
def get_model_metrics():
    """Return current model evaluation metrics (accuracy, precision, recall, F1, AUC)."""
    return {
        "metrics": model_metrics,
        "round": current_round,
        "feature_dim": fraud_feature_dim,
        "has_test_set": _X_test is not None,
    }


@app.get("/current_trust")
def get_current_trust():
    # Returns on-chain trust for clients we have seen in this run.
    result = {}
    for client_id, client_addr in client_address_mapping.items():
        result[client_id] = {
            "address": client_addr,
            "trust": contract.functions.getTrust(client_addr).call(),
            "blacklisted": contract.functions.blacklisted(client_addr).call(),
        }
    return result


@app.get("/ganache_accounts_trust")
def get_ganache_accounts_trust(limit: int = 10):
    # Helper endpoint for demos: shows on-chain trust/blacklist for Ganache accounts
    # so you can verify that malicious clients get blacklisted even if they can't
    # submitHash anymore.
    accounts = w3.eth.accounts[: max(0, limit)]
    result = {}
    for addr in accounts:
        result[addr] = {
            "trust": contract.functions.getTrust(addr).call(),
            "blacklisted": contract.functions.blacklisted(addr).call(),
        }
    return result


@app.get("/clients_snapshot")
def get_clients_snapshot():
    """
    Stable mapping for the demo clients -> Ganache accounts.
    This makes the frontend independent from in-memory `client_address_mapping`.
    """
    mapping = {
        "client_1": 1,
        "client_2": 2,
        "client_3": 3,
        "malicious_client": 4,
    }
    result = {}
    for client_id, acct_index in mapping.items():
        addr = w3.eth.accounts[acct_index]
        result[client_id] = {
            "address": addr,
            "trust": contract.functions.getTrust(addr).call(),
            "blacklisted": contract.functions.blacklisted(addr).call(),
        }
    return result


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    try:
        dashboard_path = Path(__file__).with_name("dashboard.html")
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h3>dashboard.html not found</h3>")


# ---------------------------
# Upwork-style Job Workflow
# ---------------------------

job_counter: int = 1
jobs: Dict[int, Dict[str, Any]] = {}


def _job_proof_round(job_id: int) -> int:
    return job_id * 10


def _job_ai_round(job_id: int) -> int:
    return job_id * 10 + 1


def _job_decision_round(job_id: int) -> int:
    return job_id * 10 + 2


def _sha256_bytes32_hex(text: str) -> Tuple[str, Any]:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest, bytes.fromhex(digest)


def _submit_hash_as(round_number: int, hash_bytes32: Any, sender_addr: str) -> None:
    """
    Calls contract.submitHash from `sender_addr`.
    Ganache provides unlocked accounts, so default_account switching works for demo.
    """
    previous = w3.eth.default_account
    try:
        w3.eth.default_account = to_checksum_address(sender_addr)
        # Ensure sender is registered (needed for submitHash()).
        try:
            tx_reg = contract.functions.registerClient().transact()
            w3.eth.wait_for_transaction_receipt(tx_reg)
        except Exception:
            pass
        tx = contract.functions.submitHash(round_number, hash_bytes32).transact()
        w3.eth.wait_for_transaction_receipt(tx)
    finally:
        w3.eth.default_account = previous


def _sigmoid(z: float) -> float:
    z = float(z)
    if z >= 0:
        return 1.0 / (1.0 + np.exp(-z))
    ez = np.exp(z)
    return float(ez / (1.0 + ez))


def _extract_scaled_features_from_proof(proof_text: str, job: Optional[Dict] = None) -> np.ndarray:
    """
    Build a real feature vector from structured job profile data.
    Falls back to SHA-based demo features only if no dataset/profile data available.
    """
    d = int(fraud_feature_dim)
    if d <= 0:
        return np.zeros((0,), dtype=float)

    # If we have dataset feature columns and a job with profile data, use real features
    if _dataset_feature_cols and job and job.get("profile"):
        profile = job["profile"]
        raw = np.zeros(d, dtype=float)
        for i, col in enumerate(_dataset_feature_cols):
            if i >= d:
                break
            raw[i] = float(profile.get(col, 0.0))
        # Apply same normalization as training data
        if _dataset_mean is not None and _dataset_std is not None:
            return (raw - _dataset_mean) / _dataset_std
        return raw

    # Fallback: use job metadata to build approximate features
    if job:
        raw = np.zeros(d, dtype=float)
        # Map available job context to known feature positions
        feature_map = {
            "buyer_hire_rate_pct": 50.0,
            "client_total_spent": job.get("amount", 100.0) * 10,
            "client_hires": 5.0,
            "buyer_avgHourlyJobsRate_amount": job.get("amount", 100.0) / max(1.0, job.get("deadline_hours", 1.0)),
            "fixed_budget_amount": job.get("amount", 100.0),
            "client_rating": 4.0,
            "client_reviews": 10.0,
            "phone_verified": 1.0,
            "payment_verified": 1.0,
            "isContractToHire": 0.0,
        }
        # Use on-chain trust to infer verification signals
        client_addr = job.get("client_addr")
        freelancer_addr = job.get("freelancer_addr")
        if client_addr:
            try:
                client_trust = contract.functions.getTrust(client_addr).call()
                # Map trust (0-100) to verification likelihood
                trust_ratio = min(client_trust / 100.0, 1.0)
                feature_map["phone_verified"] = trust_ratio
                feature_map["payment_verified"] = trust_ratio
                feature_map["buyer_hire_rate_pct"] = trust_ratio * 80.0
                feature_map["client_rating"] = trust_ratio * 5.0
            except Exception:
                pass
        if freelancer_addr:
            try:
                fl_trust = contract.functions.getTrust(freelancer_addr).call()
                is_blacklisted = contract.functions.blacklisted(freelancer_addr).call()
                if is_blacklisted:
                    feature_map["phone_verified"] = 0.0
                    feature_map["payment_verified"] = 0.0
            except Exception:
                pass

        for i, col in enumerate(_dataset_feature_cols or []):
            if i >= d:
                break
            raw[i] = feature_map.get(col, 0.0)

        if _dataset_mean is not None and _dataset_std is not None:
            return (raw - _dataset_mean) / _dataset_std
        return raw

    # Last resort: SHA-based features (original fallback for demo mode)
    digest = hashlib.sha256(proof_text.encode("utf-8")).digest()
    feats = np.zeros((d,), dtype=float)
    for i in range(d):
        b = digest[i % len(digest)]
        feats[i] = (b / 255.0) * 6.0 - 3.0
    return feats


class CreateJobRequest(BaseModel):
    client_index: int
    freelancer_index: int
    amount: float = 100.0
    deadline_hours: float = 0.05  # ~3 minutes for quick demo
    # Optional structured profile fields (match training dataset features)
    buyer_hire_rate_pct: Optional[float] = None
    client_total_spent: Optional[float] = None
    client_hires: Optional[float] = None
    buyer_avgHourlyJobsRate_amount: Optional[float] = None
    buyer_stats_hoursCount: Optional[float] = None
    hourly_min: Optional[float] = None
    hourly_max: Optional[float] = None
    fixed_budget_amount: Optional[float] = None
    duration: Optional[float] = None
    level: Optional[float] = None
    applicants: Optional[float] = None
    numberOfPositionsToHire: Optional[float] = None
    connects_required: Optional[float] = None
    client_rating: Optional[float] = None
    client_reviews: Optional[float] = None
    buyer_stats_activeAssignmentsCount: Optional[float] = None
    buyer_stats_totalJobsWithHires: Optional[float] = None
    clientActivity_invitationsSent: Optional[float] = None
    clientActivity_totalHired: Optional[float] = None
    clientActivity_totalInvitedToInterview: Optional[float] = None
    clientActivity_unansweredInvites: Optional[float] = None
    buyer_jobs_openCount: Optional[float] = None
    buyer_jobs_postedCount: Optional[float] = None
    phone_verified: Optional[float] = None
    isContractToHire: Optional[float] = None
    payment_verified: Optional[float] = None


class SubmitProofRequest(BaseModel):
    job_id: int
    freelancer_index: int
    proof_text: str


class RunAiRequest(BaseModel):
    job_id: int


class DecisionRequest(BaseModel):
    job_id: int
    client_index: int


@app.post("/upwork/job/create")
def upwork_create_job(req: CreateJobRequest):
    global job_counter, jobs

    client_addr = w3.eth.accounts[req.client_index]
    freelancer_addr = w3.eth.accounts[req.freelancer_index]
    created_at = int(time.time())
    deadline_until = created_at + int(req.deadline_hours * 3600)
    dispute_until = deadline_until + 86400  # +24 hours

    job_id = job_counter
    job_counter += 1

    jobs[job_id] = {
        "job_id": job_id,
        "client_index": req.client_index,
        "freelancer_index": req.freelancer_index,
        "client_addr": client_addr,
        "freelancer_addr": freelancer_addr,
        "amount": float(req.amount),
        "deadline_hours": float(req.deadline_hours),
        "created_at": created_at,
        "deadline_until": deadline_until,
        "dispute_until": dispute_until,
        "state": "CREATED",
        "proof_text": None,
        "proof_hash_hex": None,
        "ai_result": None,
        "ai_hash_hex": None,
        "decision": None,
        "decision_hash_hex": None,
        "decision_action": None,
        "profile": {},
    }

    # Store any structured profile fields provided by the frontend
    profile_fields = [
        "buyer_hire_rate_pct", "client_total_spent", "client_hires",
        "buyer_avgHourlyJobsRate_amount", "buyer_stats_hoursCount",
        "hourly_min", "hourly_max", "fixed_budget_amount", "duration",
        "level", "applicants", "numberOfPositionsToHire", "connects_required",
        "client_rating", "client_reviews", "buyer_stats_activeAssignmentsCount",
        "buyer_stats_totalJobsWithHires", "clientActivity_invitationsSent",
        "clientActivity_totalHired", "clientActivity_totalInvitedToInterview",
        "clientActivity_unansweredInvites", "buyer_jobs_openCount",
        "buyer_jobs_postedCount", "phone_verified", "isContractToHire",
        "payment_verified",
    ]
    for f in profile_fields:
        val = getattr(req, f, None)
        if val is not None:
            jobs[job_id]["profile"][f] = float(val)

    return {
        "job_id": job_id,
        "state": "CREATED",
        "client_addr": client_addr,
        "freelancer_addr": freelancer_addr,
        "deadline_until": deadline_until,
        "dispute_until": dispute_until,
    }


@app.post("/upwork/job/submit_proof")
def upwork_submit_proof(req: SubmitProofRequest):
    if req.job_id not in jobs:
        return {"ok": False, "message": "Unknown job_id"}

    job = jobs[req.job_id]
    if job["freelancer_index"] != req.freelancer_index:
        return {"ok": False, "message": "freelancer_index mismatch"}
    if job["state"] not in ("CREATED",):
        return {"ok": False, "message": f"Invalid state for submit_proof: {job['state']}"}

    proof_text = req.proof_text
    proof_hash_hex, proof_hash_bytes32 = _sha256_bytes32_hex(proof_text)

    # Commit proof hash on-chain under the freelancer address.
    _submit_hash_as(_job_proof_round(req.job_id), proof_hash_bytes32, job["freelancer_addr"])

    job["proof_text"] = proof_text
    job["proof_hash_hex"] = proof_hash_hex
    job["state"] = "PROOF_SUBMITTED"

    return {"ok": True, "job_id": req.job_id, "proof_hash_hex": proof_hash_hex}


@app.post("/upwork/job/run_ai")
def upwork_run_ai(req: RunAiRequest):
    if req.job_id not in jobs:
        return {"ok": False, "message": "Unknown job_id"}
    job = jobs[req.job_id]

    if job["state"] not in ("PROOF_SUBMITTED",):
        return {"ok": False, "message": f"Invalid state for run_ai: {job['state']}"}

    proof_text = job["proof_text"] or ""
    x_scaled = _extract_scaled_features_from_proof(proof_text, job=job)

    # riskScore from the trust-gated FL fraud model (MLP or LogReg).
    w = fraud_model_weights
    d = int(fraud_feature_dim)
    HIDDEN = 32
    expected_mlp_dim = d * HIDDEN + HIDDEN + HIDDEN + 1

    if w is not None and len(w) == expected_mlp_dim and len(x_scaled) == d:
        # MLP forward pass
        idx = 0
        W1 = w[idx:idx + d * HIDDEN].reshape(d, HIDDEN)
        idx += d * HIDDEN
        b1 = w[idx:idx + HIDDEN]
        idx += HIDDEN
        W2 = w[idx:idx + HIDDEN].reshape(HIDDEN, 1)
        idx += HIDDEN
        b2 = w[idx:idx + 1]
        z1 = x_scaled @ W1 + b1
        a1 = np.maximum(0.0, z1)
        z2 = float(a1 @ W2 + b2)
        risk_score = _sigmoid(z2)
    elif w is not None and len(x_scaled) > 0:
        # Logistic regression fallback
        x_aug = np.concatenate([x_scaled, np.array([1.0], dtype=float)], axis=0)
        if len(w) == len(x_aug):
            risk_score = _sigmoid(float(np.dot(x_aug, w)))
        else:
            risk_score = 0.5
    else:
        risk_score = 0.5

    ai_verdict = "FRAUD" if risk_score >= fraud_accept_threshold else "LEGIT"
    ai_result = {
        "riskScore": float(risk_score),
        "verdict": ai_verdict,
        "threshold": float(fraud_accept_threshold),
    }
    ai_json = json.dumps(ai_result, sort_keys=True, separators=(",", ":"))
    ai_hash_hex, ai_hash_bytes32 = _sha256_bytes32_hex(ai_json)

    # Commit AI hash under contract owner.
    owner_addr = w3.eth.accounts[0]
    _submit_hash_as(_job_ai_round(req.job_id), ai_hash_bytes32, owner_addr)

    job["ai_result"] = ai_result
    job["ai_hash_hex"] = ai_hash_hex
    job["state"] = "AI_COMMITTED"

    return {"ok": True, "job_id": req.job_id, "ai_result": ai_result, "ai_hash_hex": ai_hash_hex}


@app.post("/upwork/job/approve")
def upwork_approve(req: DecisionRequest):
    return _upwork_decide(req, action="APPROVE")


@app.post("/upwork/job/dispute")
def upwork_dispute(req: DecisionRequest):
    return _upwork_decide(req, action="DISPUTE")


def _upwork_decide(req: DecisionRequest, action: str):
    if req.job_id not in jobs:
        return {"ok": False, "message": "Unknown job_id"}
    job = jobs[req.job_id]

    if job["client_index"] != req.client_index:
        return {"ok": False, "message": "client_index mismatch"}
    if job["state"] not in ("AI_COMMITTED",):
        return {"ok": False, "message": f"Invalid state for decision: {job['state']}"}

    now = int(time.time())
    if action == "DISPUTE":
        if now > job["dispute_until"]:
            return {"ok": False, "message": "Dispute window closed"}

    ai_result = job["ai_result"] or {}
    is_legit = ai_result.get("verdict") == "LEGIT"

    # Decide status (payment style A: release/reject/dispute-resolved flags).
    if action == "APPROVE":
        decision = "PAYMENT_RELEASED" if is_legit else "PAYMENT_REJECTED"
    else:
        # DISPUTE: resolve to same outcome for demo.
        decision = "DISPUTE_CLOSED_RELEASED" if is_legit else "DISPUTE_CLOSED_REFUNDED"

    # Penalize parties based on consistency with AI.
    # - Freelancer is penalized if AI says FRAUD.
    # - Client is penalized if they choose an action inconsistent with AI verdict.
    try:
        owner_addr = w3.eth.accounts[0]
        # penalize freelancer if AI says fraud
        if not is_legit:
            tx_f = contract.functions.penalizeClient(job["freelancer_addr"]).transact()
            w3.eth.wait_for_transaction_receipt(tx_f)

        # penalize client if approves despite fraud (or disputes despite legit)
        client_inconsistent = (action == "APPROVE" and not is_legit) or (action == "DISPUTE" and is_legit)
        if client_inconsistent:
            tx_c = contract.functions.penalizeClient(job["client_addr"]).transact()
            w3.eth.wait_for_transaction_receipt(tx_c)
    except Exception:
        pass

    decision_payload = {
        "job_id": req.job_id,
        "action": action,
        "decision": decision,
        "ai_hash_hex": job.get("ai_hash_hex"),
    }
    decision_json = json.dumps(decision_payload, sort_keys=True, separators=(",", ":"))
    decision_hash_hex, decision_hash_bytes32 = _sha256_bytes32_hex(decision_json)

    # Commit decision on-chain under owner.
    owner_addr = w3.eth.accounts[0]
    _submit_hash_as(_job_decision_round(req.job_id), decision_hash_bytes32, owner_addr)

    job["decision"] = decision
    job["decision_hash_hex"] = decision_hash_hex
    job["decision_action"] = action
    job["state"] = "DECIDED"

    return {
        "ok": True,
        "job_id": req.job_id,
        "decision": decision,
        "decision_hash_hex": decision_hash_hex,
    }


@app.get("/upwork/job/status")
def upwork_job_status(job_id: int):
    if job_id not in jobs:
        return {"ok": False, "message": "Unknown job_id"}
    job = jobs[job_id]

    owner_addr = w3.eth.accounts[0]
    # Read commitments from on-chain storage.
    proof_onchain = contract.functions.updateHashes(_job_proof_round(job_id), job["freelancer_addr"]).call()
    ai_onchain = contract.functions.updateHashes(_job_ai_round(job_id), owner_addr).call()
    decision_onchain = contract.functions.updateHashes(_job_decision_round(job_id), owner_addr).call()

    def b32_to_hex(b: Any) -> str:
        # Web3 returns bytes32 as bytes-like; represent as 0x...
        if b is None:
            return ""
        if isinstance(b, (bytes, bytearray)):
            return "0x" + b.hex()
        return str(b)

    return {
        "ok": True,
        "job": {
            "job_id": job_id,
            "state": job["state"],
            "amount": job["amount"],
            "created_at": job["created_at"],
            "deadline_until": job["deadline_until"],
            "dispute_until": job["dispute_until"],
            "client_addr": job["client_addr"],
            "freelancer_addr": job["freelancer_addr"],
            "proof_hash_hex": job.get("proof_hash_hex"),
            "ai_result": job.get("ai_result"),
            "ai_hash_hex": job.get("ai_hash_hex"),
            "decision": job.get("decision"),
            "decision_hash_hex": job.get("decision_hash_hex"),
            "onchain_commitments": {
                "proof_round": _job_proof_round(job_id),
                "proof_hash_onchain": b32_to_hex(proof_onchain),
                "ai_round": _job_ai_round(job_id),
                "ai_hash_onchain": b32_to_hex(ai_onchain),
                "decision_round": _job_decision_round(job_id),
                "decision_hash_onchain": b32_to_hex(decision_onchain),
            },
            "trust": {
                "client": {
                    "trust": contract.functions.getTrust(job["client_addr"]).call(),
                    "blacklisted": contract.functions.blacklisted(job["client_addr"]).call(),
                },
                "freelancer": {
                    "trust": contract.functions.getTrust(job["freelancer_addr"]).call(),
                    "blacklisted": contract.functions.blacklisted(job["freelancer_addr"]).call(),
                },
            },
        }
    }


@app.get("/run", response_class=HTMLResponse)
def run_page():
    try:
        run_path = Path(__file__).with_name("run.html")
        with open(run_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h3>run.html not found</h3>")


@app.get("/results", response_class=HTMLResponse)
def results_page():
    try:
        results_path = Path(__file__).with_name("results.html")
        with open(results_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h3>results.html not found</h3>")


def _serve_static_html(filename: str) -> HTMLResponse:
    try:
        from pathlib import Path

        p = Path(__file__).with_name(filename)
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse(f"<h3>{filename} not found</h3>")


@app.get("/upwork/create", response_class=HTMLResponse)
def upwork_create_page():
    return _serve_static_html("upwork_create.html")


@app.get("/upwork/submit_proof", response_class=HTMLResponse)
def upwork_submit_proof_page():
    return _serve_static_html("upwork_submit_proof.html")


@app.get("/upwork/run_ai", response_class=HTMLResponse)
def upwork_run_ai_page():
    return _serve_static_html("upwork_run_ai.html")


@app.get("/upwork/decision", response_class=HTMLResponse)
def upwork_decision_page():
    return _serve_static_html("upwork_decision.html")


@app.get("/upwork/results", response_class=HTMLResponse)
def upwork_results_page():
    return _serve_static_html("upwork_results.html")


@app.get("/demo", response_class=HTMLResponse)
def demo_page():
    # Minimal dashboard for hackathon/demo purposes.
    # Shows on-chain trust/blacklist + trust evolution chart.
    try:
        from pathlib import Path

        demo_path = Path(__file__).with_name("demo.html")
        with open(demo_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse(
            "<h3>demo.html not found.</h3>"
            "<p>Expected: <code>backend/server/demo.html</code></p>"
        )
   