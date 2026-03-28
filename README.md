# Selective Blockchain Trust Layer for Federated Learning

A full-stack platform that combines **federated learning**, **blockchain-backed trust scoring**, and an **AI-powered job marketplace** to solve trust, fraud, and dispute problems in freelancing. Instead of blind reputation systems, every claim is verified on-chain and validated by anomaly detection before trust is granted.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Solution Overview](#solution-overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [1. Blockchain Setup](#1-blockchain-setup)
  - [2. Backend Setup](#2-backend-setup)
  - [3. Frontend Setup](#3-frontend-setup)
  - [4. Run Federated Learning Demo](#4-run-federated-learning-demo)
- [Core Features](#core-features)
  - [On-Chain Trust Scoring](#on-chain-trust-scoring)
  - [Federated Learning with Byzantine Resilience](#federated-learning-with-byzantine-resilience)
  - [Malicious Client Detection](#malicious-client-detection)
  - [AI-Powered Job Marketplace](#ai-powered-job-marketplace)
  - [Fraud Detection Pipeline](#fraud-detection-pipeline)
- [Smart Contract](#smart-contract)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Frontend Routes](#frontend-routes)
- [Environment Variables](#environment-variables)
- [Dataset](#dataset)
- [Contributing](#contributing)
- [License](#license)

---

## Problem Statement

Freelancing platforms today face critical trust failures on both sides:

- **Freelancers** deal with disappearing clients, unpaid invoices, and questioned proof of work.
- **Clients** encounter fake profiles, manipulated reviews, and poor-quality deliverables.
- **Platforms** struggle with payment fraud, unresolvable disputes, and centralized reputation systems easily gamed by bad actors.

An estimated 20–30% of platform reviews are fake, and 30–40% of freelancers report payment issues. Current trust systems address only 50–60% of these problems.

## Solution Overview

**Selective Blockchain Trust Layer** replaces blind trust with a three-step model:

> **Verify → Analyze → Trust**

| Layer | Mechanism | Purpose |
|---|---|---|
| **Blockchain** | Solidity smart contract on Ethereum (Ganache dev) | Immutable trust scores, commitment hashing, blacklisting |
| **Federated Learning** | Byzantine-resilient aggregation with trust-weighted trimmed mean | Collaborative fraud model training without sharing raw data |
| **Anomaly Detection** | Mahalanobis distance + cosine similarity gate | Detect poisoning attacks and malicious weight updates |
| **AI Review** | LLM-powered milestone evaluation | Automated quality scoring of deliverables against acceptance criteria |
| **Fraud MLP** | Neural network trained on transaction data | Real-time fraud risk scoring for freelancer submissions |

---

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   React UI   │────▶│  FastAPI Server   │────▶│  Ganache / EVM   │
│  (Vite/3D)   │◀────│  (Python/uvicorn) │◀────│  (Hardhat)       │
└──────────────┘     └────────┬─────────┘     └──────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
              ┌─────▼─────┐     ┌───────▼───────┐
              │ PostgreSQL │     │ FL Clients    │
              │ / SQLite   │     │ (1..N agents) │
              └────────────┘     └───────────────┘
```

**Data flow for federated learning:**

1. Clients fetch the global model from the server.
2. Each client trains locally on its data partition.
3. Clients commit a SHA-256 hash of their weights on-chain via `submitHash()`.
4. Clients submit weight updates to the server.
5. The server verifies the on-chain hash matches, runs anomaly detection, and penalizes or rewards accordingly.
6. Accepted updates are aggregated via trust-weighted trimmed mean.
7. The global model is updated, and trust scores are written back on-chain.

---

## Tech Stack

| Component | Technology |
|---|---|
| **Backend** | Python 3.10+, FastAPI, uvicorn, SQLAlchemy ORM |
| **Frontend** | React 19, Vite, React Router v7, Three.js, GSAP, Framer Motion |
| **Blockchain** | Solidity 0.8.24, Hardhat 2.22, Ganache (local dev chain) |
| **Web3** | Web3.py (backend ↔ contract interaction) |
| **Database** | PostgreSQL (production) / SQLite (dev fallback) |
| **ML** | NumPy (MLP, Mahalanobis distance, cosine similarity) |
| **AI Review** | GitHub Models API (GPT-4o-mini) |
| **Auth** | JWT (HS256, python-jose), bcrypt (passlib) |

---

## Project Structure

```
selective-blockchain-trust-layer-fl/
├── backend/
│   ├── server/
│   │   ├── main.py                 # FastAPI app, FL logic, startup training
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   ├── database.py             # DB engine & session management
│   │   ├── auth_routes.py          # /auth/signup, /auth/login
│   │   ├── auth_utils.py           # JWT creation & verification
│   │   ├── feature_routes.py       # /user, /subscription, /jobs endpoints
│   │   ├── blockchain_interface.py # Web3.py contract interaction
│   │   ├── init_db.sql             # Reference SQL schema
│   │   └── *.html                  # Fallback HTML dashboards
│   ├── clients/
│   │   ├── client_base.py          # Base federated learning client
│   │   ├── client1.py              # Honest client (account[1])
│   │   ├── client2.py              # Honest client (account[2])
│   │   ├── client3.py              # Honest client (account[3])
│   │   └── malicious_client.py     # 80% label-flip attacker (account[4])
│   ├── common/
│   │   └── dataset_utils.py        # Auto-detect labels, train/test split
│   ├── blockchain_connect.py       # Standalone Web3 connection test
│   └── requirements.txt            # Python dependencies
├── blockchain/
│   ├── contracts/
│   │   └── TrustLayer.sol          # Smart contract (trust, penalties, blacklist)
│   ├── scripts/
│   │   └── deploy.js               # Hardhat deployment script
│   ├── hardhat.config.js           # Hardhat config (Ganache at 7545)
│   └── package.json                # Node dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Route definitions
│   │   ├── api.js                  # API client (auth, jobs, FL, user)
│   │   ├── components/
│   │   │   ├── Scene3D.jsx         # Three.js hero visualization
│   │   │   ├── TrustChart.jsx      # Trust evolution chart
│   │   │   ├── Nav.jsx             # Navigation bar
│   │   │   └── LetterForm.jsx      # Letter component
│   │   └── pages/                  # Dashboard, Demo, Run, Results, Upwork*
│   ├── vite.config.js              # Vite config (proxy to :8000)
│   └── package.json                # React dependencies
├── data/
│   └── transactions.csv            # Transaction dataset for training
├── scripts/
│   └── generate_transactions_dataset.py  # Synthetic data generator
├── plot_trust.py                   # Trust score visualization script
└── README.md
```

---

## Getting Started

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| **Python** | 3.10+ | Backend server and FL clients |
| **Node.js** | 18+ | Blockchain tooling and frontend |
| **npm** | 9+ | Package management |
| **Ganache** | Latest | Local Ethereum development chain |
| **PostgreSQL** | 14+ (optional) | Production database |

### 1. Blockchain Setup

```bash
# Start Ganache (GUI or CLI) on port 7545
ganache-cli -p 7545

# In a new terminal:
cd blockchain
npm install
npx hardhat compile
npx hardhat run scripts/deploy.js --network ganache
```

Note the deployed contract address from the output. Update it in `backend/server/blockchain_interface.py` if it differs from the default (`0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512`).

### 2. Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

**Configure the database** (optional — defaults to SQLite in-memory):

```bash
# Create backend/server/.env
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require
```

**Start the server:**

```bash
cd backend/server
uvicorn main:app --reload --port 8000
```

The server will:
1. Auto-create database tables.
2. Load `data/transactions.csv` and train the fraud detection model.
3. Initialize the anomaly detector for federated learning.
4. Serve the API at `http://127.0.0.1:8000`.

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API calls are proxied to the backend at port 8000.

**Production build:**

```bash
npm run build
# Output in dist/
```

### 4. Run Federated Learning Demo

With the backend and Ganache running, open separate terminals for each client:

```bash
# Terminal 1 — Honest client
cd backend/clients
python client1.py

# Terminal 2 — Honest client
python client2.py

# Terminal 3 — Honest client
python client3.py

# Terminal 4 — Malicious client (80% label-flip attack)
python malicious_client.py
```

Each client will:
1. Register on-chain via `registerClient()`.
2. Fetch the global model.
3. Train locally (the malicious client flips 80% of labels).
4. Commit weight hash on-chain and submit the update to the server.

Trigger aggregation via the `/aggregate` endpoint or through the **Run** page in the frontend. The malicious client will be detected, penalized, and eventually blacklisted.

---

## Core Features

### On-Chain Trust Scoring

Every participant has a trust score managed by the `TrustLayer` smart contract:

| Parameter | Value |
|---|---|
| Initial trust | 100 |
| Penalty per offense | −20 |
| Reward per honest round | +5 |
| Maximum trust | 120 |
| Blacklist threshold | < 40 |

Trust scores are fully on-chain and queryable by any participant. Blacklisted addresses cannot submit further updates.

### Federated Learning with Byzantine Resilience

- **Aggregation**: Trust-weighted trimmed mean when ≥ 4 clients participate; trust-weighted average otherwise.
- **Weight validation**: On-chain hash commitment prevents tampering between submission and aggregation.
- **Model**: MLP neural network trained on transaction fraud data with Xavier initialization.
- **Evaluation**: Per-round accuracy, precision, recall, F1, and AUC metrics on a held-out test set.

### Malicious Client Detection

Two-layer detection pipeline:

1. **On-Chain Hash Verification** — The SHA-256 hash of submitted weights must match the pre-committed on-chain hash. Any mismatch triggers an immediate penalty.

2. **Statistical Anomaly Detection** — The deviation vector (`local_weights − global_weights`) is analyzed using:
   - **Mahalanobis distance** against the learned honest deviation distribution (99.5th percentile threshold).
   - **Cosine similarity** check to catch directional and scaling attacks.

Flagged clients receive on-chain penalties. After repeated offenses (trust < 40), they are permanently blacklisted.

### AI-Powered Job Marketplace

A full Upwork-style freelancing workflow with milestone-based jobs:

1. **Job Creation** — Clients define jobs with budgets, required skills, and milestones (each with acceptance criteria, deadlines, and payouts).
2. **Application & Gating** — Freelancers apply; low-confidence workers with prior job history require premium subscriptions. Blacklisted addresses are blocked.
3. **Proof Submission** — Freelancers submit GitHub repository URLs as proof. The system fetches the latest commit SHA and timestamp, verifying deadline compliance.
4. **AI Review** — An LLM evaluates the submission against acceptance criteria, returning a quality score (0–100) and detailed analysis.
5. **Approval / Dispute** — Clients approve milestones (triggering payment) or raise disputes for resolution.
6. **Review & Rating** — Clients rate freelancers (1–5 stars) which feeds into cumulative worker scores.

### Fraud Detection Pipeline

- **MLP Classifier** trained on transaction features from `data/transactions.csv`.
- **Feature extraction** from freelancer profile and job context at submission time.
- **Real-time scoring** returns a fraud risk value (0–1) for every milestone submission.
- **Z-score normalization** using dataset statistics ensures consistent feature scaling.

---

## Smart Contract

**File:** `blockchain/contracts/TrustLayer.sol`

```solidity
// Key functions
function registerClient() external
function submitHash(uint256 round, bytes32 hash) external
function penalizeClient(address client) external   // server-only
function rewardClient(address client) external     // server-only
function getTrust(address client) external view returns (uint256)
```

**Events:**
- `ClientRegistered(address client)`
- `HashSubmitted(address client, uint256 round, bytes32 hash)`
- `TrustUpdated(address client, uint256 newTrust)`
- `Blacklisted(address client)`
- `ClientRewarded(address client, uint256 newTrust)`

**Deployment:**

```bash
cd blockchain
npx hardhat run scripts/deploy.js --network ganache
```

---

## API Reference

### Authentication (`/auth`)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/signup` | Register (email, password, name, role) → JWT token |
| POST | `/auth/login` | Authenticate → JWT token |

### User Profile (`/user`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/user/profile` | Current user profile with unified trust score |
| PUT | `/user/profile` | Update profile fields |
| GET | `/user/profile/{user_id}` | Public profile view |
| POST | `/user/link_wallet` | Link Ethereum wallet address |
| GET | `/user/trust_history` | User's trust score history |

**Unified Trust Score Formula:**

```
trust = 0.40 × blockchain_trust + 0.35 × ai_confidence + 0.25 × ai_quality − fraud_penalty
```

### Subscription (`/subscription`)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/subscription/subscribe` | Subscribe to a tier (`free` / `premium`) |
| GET | `/subscription/status` | Current tier and expiration |

### Jobs (`/jobs`)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/jobs/create` | Create job with milestones (premium required) |
| GET | `/jobs/list` | List jobs (filter by status, skills) |
| GET | `/jobs/{job_id}` | Full job detail with milestone analyses |
| POST | `/jobs/{job_id}/apply` | Apply as freelancer |
| POST | `/jobs/{job_id}/milestones/{step}/submit` | Submit proof (GitHub URL) |
| POST | `/jobs/{job_id}/run_ai` | Run LLM review on submission |
| POST | `/jobs/{job_id}/approve` | Approve milestone and release payment |
| POST | `/jobs/{job_id}/dispute` | Raise dispute on milestone |
| POST | `/jobs/{job_id}/review` | Submit rating (1–5) and comment |
| POST | `/jobs/{job_id}/match_freelancers` | Match freelancers by skills and trust |

### Federated Learning

| Method | Endpoint | Description |
|---|---|---|
| GET | `/get_global_model` | Fetch current global weights and round |
| POST | `/submit_update` | Submit local weight update |
| POST | `/aggregate` | Trigger trust-weighted aggregation |
| GET | `/trust_history` | All clients' trust scores across rounds |
| GET | `/current_trust` | Current on-chain trust for all clients |
| GET | `/ganache_accounts_trust` | Ganache account trust + blacklist status |
| GET | `/clients_snapshot` | Demo client → Ganache account mapping |
| GET | `/model_metrics` | Accuracy, precision, recall, F1, AUC |

---

## Database Schema

| Table | Description |
|---|---|
| `users` | Accounts with role (client/freelancer), wallet address, trust score, profile fields |
| `subscriptions` | Tier (free/premium) with expiration tracking |
| `jobs` | Job postings with budget, required skills, step counter, status |
| `milestones` | Individual steps: acceptance criteria, deadline, payout, AI analysis, GitHub proof |
| `worker_scores` | Cumulative metrics: quality, deadline adherence, confidence, fraud flags |
| `reviews` | Client-to-freelancer ratings (1–5) with comments |

Tables are auto-created on server startup via SQLAlchemy's `Base.metadata.create_all()`.

---

## Frontend Routes

| Route | Page | Description |
|---|---|---|
| `/` | Home | Landing page with 3D hero visualization |
| `/login` | Login | Email/password authentication |
| `/signup` | Sign Up | Account registration |
| `/dashboard` | Dashboard | Live trust evolution charts, on-chain snapshot |
| `/run` | Run | Trigger federated learning aggregation rounds |
| `/results` | Results | Model metrics and round summary |
| `/demo` | Demo | Interactive 3D trust visualization |
| `/upwork/create` | Create Job | Define jobs with milestones, budget, skills |
| `/upwork/submit_proof` | Submit Proof | Upload GitHub repo URL for milestone |
| `/upwork/run_ai` | Run AI | Trigger LLM-powered review of submission |
| `/upwork/decision` | Decision | Approve or dispute milestone |
| `/upwork/results` | Results | Final payment status and reviews |

---

## Environment Variables

Create a `.env` file in `backend/server/`:

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | SQLite in-memory | PostgreSQL connection string |
| `JWT_SECRET` | No | `trustscore-secret-change-in-production` | Secret key for JWT tokens |
| `GITHUB_TOKEN` | No | — | GitHub Models API token (for AI review) |

**Blockchain configuration** is set in:
- `blockchain/hardhat.config.js` — Ganache URL (`http://127.0.0.1:7545`)
- `backend/server/blockchain_interface.py` — Contract address and Ganache URL

---

## Dataset

**Location:** `data/transactions.csv`

The platform trains its fraud detection model on a tabular transaction dataset. The dataset loader auto-detects:
- **Label column**: `is_fraud`, `fraud`, `label`, `target`, `class`, or `y`
- **Feature columns**: All numeric columns (excluding the label)

**Generate synthetic data:**

```bash
python scripts/generate_transactions_dataset.py
```

**Data processing:**
- 80/20 stratified train/test split (seed: 99)
- Z-score normalization
- Minimum 1 sample per class in test set

---

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Commit changes: `git commit -m "Add your feature"`.
4. Push to the branch: `git push origin feature/your-feature`.
5. Open a pull request.

---

## License

This project is open-source. See the repository for license details.
