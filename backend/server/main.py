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

app = FastAPI()

if _AUTH_AVAILABLE and auth_router:
    app.include_router(auth_router)

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

current_round = 1
expected_clients = 3 
client_updates = {} 
submitted_clients = set()
trust_history = {}
client_address_mapping = {}

class MahalanobisAnomalyDetector:
    """
    Statistical anomaly detector trained on "honest deviations".
    Flags updates with high Mahalanobis distance from the learned mean/covariance.
    """

    def __init__(self, threshold_percentile: float = 0.995, epsilon: float = 1e-6):
        self.threshold_percentile = threshold_percentile
        self.epsilon = epsilon
        self.mean = None
        self.cov_inv = None
        self.threshold = None

    def fit(self, X: np.ndarray) -> None:
        # X: (n_samples, n_features)
        self.mean = np.mean(X, axis=0)
        cov = np.cov(X.T, bias=True)
        cov = cov + self.epsilon * np.eye(cov.shape[0])
        self.cov_inv = np.linalg.inv(cov)

        md2_scores = self.score_samples(X)
        self.threshold = float(np.quantile(md2_scores, self.threshold_percentile))

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        diffs = X - self.mean
        left = diffs @ self.cov_inv
        md2 = np.sum(left * diffs, axis=1)
        return md2

    def predict_one(self, x: np.ndarray) -> tuple[bool, float]:
        x2 = x.reshape(1, -1)
        md2 = float(self.score_samples(x2)[0])
        return md2 > self.threshold, md2


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

    # If dataset exists, train the anomaly detector on *realistic* honest
    # logistic-regression weight vectors generated from the dataset.
    try:
        X_scaled, y, feature_cols, label_col, mean, std = load_dataset_scaled(DEFAULT_DATASET_PATH)
        participants = 4
        dim = int(X_scaled.shape[1]) + 1  # +1 for bias weight
        global_model = np.zeros(dim, dtype=float)
        print(
            f"Dataset detected: label={label_col}, features={len(feature_cols)} (model_dim={dim}). Training ML gate..."
        )

        def sigmoid(z: np.ndarray) -> np.ndarray:
            out = np.empty_like(z, dtype=float)
            pos = z >= 0
            out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
            exp_z = np.exp(z[~pos])
            out[~pos] = exp_z / (1.0 + exp_z)
            return out

        def train_logreg_gd(X_part: np.ndarray, y_part: np.ndarray, w_init: np.ndarray, lr: float, epochs: int, reg_lambda: float) -> np.ndarray:
            n = X_part.shape[0]
            X_aug = np.concatenate([X_part, np.ones((n, 1), dtype=float)], axis=1)
            w = w_init.astype(float).copy()
            for _ in range(epochs):
                z = X_aug @ w
                p = sigmoid(z)
                grad = (X_aug.T @ (p - y_part)) / n
                # L2 regularization on coefficients only (exclude bias)
                grad[:-1] += reg_lambda * w[:-1]
                w = w - lr * grad
            return w

        rng = np.random.default_rng(42)
        idx = np.arange(X_scaled.shape[0])
        n_gate_samples = 200  # must be > dim for stable covariance
        epochs = 25
        lr = 0.35
        reg_lambda = 0.01
        sample_size = min(500, X_scaled.shape[0] // participants)

        weights_samples: List[np.ndarray] = []
        for i in range(n_gate_samples):
            client_part = i % participants
            part_mask = (idx % participants) == client_part
            part_idx = idx[part_mask]
            if len(part_idx) == 0:
                continue
            chosen = rng.choice(part_idx, size=min(sample_size, len(part_idx)), replace=False)
            X_part = X_scaled[chosen]
            y_part = y[chosen]
            w = train_logreg_gd(X_part, y_part, w_init=global_model, lr=lr, epochs=epochs, reg_lambda=reg_lambda)
            weights_samples.append(w)

        X_train = np.vstack(weights_samples) if weights_samples else np.zeros((1, dim))
        anomaly_detector.fit(X_train)
        print(f"ML anomaly detector trained on dataset gate: md2_threshold={anomaly_detector.threshold:.6f} (dim={dim}, n={X_train.shape[0]})")

        # Train a trust-gated global fraud model (federated style).
        participants = 4
        fraud_feature_dim = int(X_scaled.shape[1])

        local_weights: List[np.ndarray] = []
        accepted_weights: List[np.ndarray] = []
        for part in range(participants):
            part_mask = (idx % participants) == part
            X_part = X_scaled[part_mask]
            y_part = y[part_mask].copy()

            # Simulate one malicious participant by label-flipping (for the ML trust gate demo).
            if part == 3:
                rng_part = np.random.default_rng(123 + int(part))
                flip_mask = rng_part.random(size=y_part.shape[0]) < 0.35
                y_part = np.where(flip_mask, 1.0 - y_part, y_part)

            w_local = train_logreg_gd(
                X_part,
                y_part,
                w_init=global_model,
                lr=lr,
                epochs=18,
                reg_lambda=reg_lambda,
            )
            local_weights.append(w_local)

            deviation_vec = w_local - global_model
            is_malicious, _ = anomaly_detector.predict_one(deviation_vec)
            if not is_malicious:
                accepted_weights.append(w_local)

        if accepted_weights:
            fraud_model_weights = np.mean(np.vstack(accepted_weights), axis=0)
        else:
            # If detector rejects everything (unlikely), fall back to average of all.
            fraud_model_weights = np.mean(np.vstack(local_weights), axis=0)

        fraud_feature_dim = int(X_scaled.shape[1])
        print(
            f"Trust-gated fraud model ready: dim={fraud_feature_dim} "
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

    return {
        "message": "Update accepted",
        "trust": trust,
        "current_round": current_round,
        "md2_score": md2_score,
        "hash_matches": hash_matches,
    }

# 🔥 NEW: Aggregation endpoint
@app.post("/aggregate")
def aggregate():
    global global_model, current_round
    global client_updates, submitted_clients
    global trust_history, client_address_mapping

    accepted_updates_count = len(client_updates)

    # 🔥 1️⃣ Federated Averaging (only if we have accepted updates)
    if accepted_updates_count > 0:
        updates = list(client_updates.values())
        global_model = np.mean(updates, axis=0)

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


def _extract_scaled_features_from_proof(proof_text: str) -> np.ndarray:
    """
    For demo: convert proof text into a fixed-length scaled feature vector
    compatible with the fraud_model_weights trained on your dataset features.
    """
    d = int(fraud_feature_dim)
    if d <= 0:
        return np.zeros((0,), dtype=float)

    digest = hashlib.sha256(proof_text.encode("utf-8")).digest()
    # Map bytes -> [-3, 3] range.
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
    }

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
    x_scaled = _extract_scaled_features_from_proof(proof_text)

    # riskScore from the trust-gated FL fraud model.
    w = fraud_model_weights
    x_aug = np.concatenate([x_scaled, np.array([1.0], dtype=float)], axis=0)
    if w is None or len(w) != len(x_aug):
        # Safety fallback
        risk_score = 0.5
    else:
        risk_score = _sigmoid(float(np.dot(x_aug, w)))

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
   