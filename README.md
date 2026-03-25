# Hi there! I'm Ayush Bisht

I’m a Computer Science student at **Meerut Institute of Engeneering and Technology**.

## About Me
- 🔭 I’m currently working on **App Development**
- 🌱 I’m currently learning **App Development and DSA**
- 💡 I love to explore new things in tech

## Languages & Tools
aws • azure • bash • c • css3 • docker • express • git • html5 • java • javascript • linux • materialize • mongodb • mysql • nextjs • nodejs • postman • python • react • tailwind • typescript • wx_widgets

<!--
# Blockchain-Backed Federated Learning Trust System

A simulation project that combines federated learning (FL) with a blockchain trust layer. Clients submit local model updates to a Python aggregator, while update hashes and trust scores are managed on-chain through a Solidity smart contract.

This repository demonstrates how to:
- accept FL model updates from multiple clients,
- detect suspicious updates with a server-side anomaly check,
- penalize malicious behavior using a smart contract,
- reject low-trust clients,
- track trust evolution round by round.

## What This Project Contains

- `backend/server/main.py`: FastAPI aggregator server.
- `backend/server/blockchain_interface.py`: Web3 + contract binding used by server.
- `backend/clients/client_base.py`: shared FL client implementation.
- `backend/clients/client1.py`, `client2.py`, `client3.py`: normal and mixed-behavior clients.
- `backend/clients/malicious_client.py`: strongly poisoned client.
- `blockchain/contracts/TrustLayer.sol`: trust management smart contract.
- `blockchain/scripts/deploy.js`: deployment script.
- `plot_trust.py`: trust score visualization from server state.

## Architecture

```text
+-----------------------------+        +------------------------------+
|   FL Clients (Python)       |        |   FastAPI Aggregator Server  |
| - train local weights       | -----> | /submit_update               |
| - hash update               |        | - anomaly detection          |
| - submit hash on-chain      |        | - trust check via contract   |
+-----------------------------+        | - stores valid updates       |
          |                            +---------------+--------------+
          |                                            |
          v                                            v
+-----------------------------+        +------------------------------+
|   TrustLayer.sol            | <----> |   Ganache Local Blockchain   |
| - register client           |        | - accounts/transactions      |
| - store update hash         |        | - contract state             |
| - penalize + blacklist      |        +------------------------------+
+-----------------------------+
```

## End-to-End Flow

1. A client registers on-chain (`registerClient`).
2. Client fetches current global model from server (`/get_global_model`).
3. Client trains locally (noise-based simulation).
4. Client hashes local weights and submits hash on-chain (`submitHash(round, hash)`).
5. Client sends raw weights to server (`/submit_update`).
6. Server computes deviation from current global model.
7. If deviation is high, server penalizes client on-chain (`penalizeClient`).
8. If trust is below threshold, update is rejected.
9. Valid updates are aggregated by calling `/aggregate`.
10. Server records trust history and advances round.

## Trust Model (Smart Contract)

Defined in `TrustLayer.sol`:
- `INITIAL_TRUST = 100`
- `PENALTY = 20`
- `THRESHOLD = 40`

Behavior:
- New registered clients start at trust 100.
- Penalty subtracts 20 each time malicious behavior is detected.
- Once trust drops below 40, client is blacklisted.
- Blacklisted clients cannot submit update hashes.

## Detection Logic (Server)

In `backend/server/main.py`:
- Server computes `deviation = ||weights - global_model||` (L2 norm).
- Current dynamic threshold is hardcoded as `2.0`.
- If deviation > 2.0, the update is considered malicious and the client is penalized.
- If trust < contract threshold, update is rejected.
- Otherwise update is accepted for aggregation.

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- Ganache GUI or Ganache CLI

## Setup

## 1) Install blockchain dependencies

```bash
cd blockchain
npm install
```

## 2) Start Ganache

Run Ganache on:
- RPC URL: `http://127.0.0.1:7545`

Important:
- The server must use an account that is the **contract owner** to call `penalizeClient`.
- In `backend/server/blockchain_interface.py`, default account is set to `w3.eth.accounts[0]`.
- Ensure contract was deployed from the same address, or update the default account logic.

## 3) Deploy contract

```bash
cd blockchain
npx hardhat run scripts/deploy.js --network ganache
```

Copy deployed contract address from output.

## 4) Update contract address references

Update these files with the new deployed address:
- `backend/server/blockchain_interface.py` (`contract_address`)
- `backend/clients/client_base.py` (`CONTRACT_ADDRESS`)

ABI must match deployed contract. The current ABI is inlined in both files.

## 5) Install Python dependencies

From repository root:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn numpy requests web3 matplotlib pydantic
```

## Running the System

Because `backend/server/main.py` imports `blockchain_interface` as a local module, start server from `backend/server` directory.

## 1) Start aggregator server

```bash
cd backend/server
uvicorn main:app --reload --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/
```

## 2) Run clients (new terminal, repo root)

Run clients as modules so relative imports work:

```bash
python -m backend.clients.client1
python -m backend.clients.client2
python -m backend.clients.client3
```

Optional malicious client:

```bash
python -m backend.clients.malicious_client
```

## 3) Trigger aggregation

After desired client submissions for current round:

```bash
curl -X POST http://127.0.0.1:8000/aggregate
```

Repeat client submissions and aggregation for multiple rounds.

## 4) View trust history

```bash
curl http://127.0.0.1:8000/trust_history
```

## 5) Plot trust evolution

From repo root:

```bash
python plot_trust.py
```

## API Reference

## `GET /`

Returns server status.

Example response:

```json
{"message": "Aggregator Server is running"}
```

## `GET /get_global_model`

Returns current round and global model weights.

Example response:

```json
{
  "round": 1,
  "weights": [0.5, 0.5, 0.5]
}
```

## `POST /submit_update`

Submit a client model update.

Request body:

```json
{
  "client_id": "client_1",
  "client_address": "0x...",
  "weights": [0.61, 0.43, 0.52]
}
```

Possible responses include:
- `Update accepted`
- `Client penalized for malicious update`
- `Client rejected due to low trust`
- `Already submitted for this round`

## `POST /aggregate`

Runs federated averaging on accepted updates, records trust snapshot, clears round buffers, and increments round.

## `GET /trust_history`

Returns historical trust values captured per round.

## Client Behavior Profiles

- `client1.py`: honest client.
- `client2.py`: alternates behavior; malicious on even rounds.
- `client3.py`: honest client.
- `malicious_client.py`: submits strongly poisoned update (`+ [50, 50, 50]`).

## Results and Analysis

Place your figure files in `docs/images/` using the exact names below.

<figure>
  <img src="docs/images/trust-evolution.png" alt="Line chart of trust evolution across rounds where client_1 stays at trust 100, client_2 declines from 100 to 60, and malicious_client drops from 80 to 20 by round 3." width="900" />
  <figcaption>
    <strong>Trust Evolution Across Rounds.</strong>
    This plot shows the on-chain trust mechanism differentiating client behavior over time. `client_1` stays at 100, indicating consistently acceptable updates. `client_2` declines from 100 to 60, which reflects intermittent malicious behavior and periodic penalties. `malicious_client` falls quickly from 80 to 20, showing strong enforcement against persistent adversarial updates.
  </figcaption>
</figure>

<figure>
  <img src="docs/images/accuracy-comparison.png" alt="Line chart comparing validation accuracy under adversarial attack: Vanilla FL decreases from about 92% to 57%, while Selective Trust FL declines only from about 92% to 85% over ten rounds." width="900" />
  <figcaption>
    <strong>Model Accuracy Under Adversarial Attack.</strong>
    Vanilla federated averaging degrades steadily as poisoned updates influence the global model. Selective Trust FL maintains significantly higher validation accuracy by reducing the impact of low-trust participants. The widening gap between curves across rounds indicates improved robustness of trust-aware aggregation.
  </figcaption>
</figure>

<figure>
  <img src="docs/images/gas-cost-comparison.png" alt="Bar chart comparing gas usage per training round: Fully On-Chain uses 1,500,000 gas and Semi-On-Chain uses 120,000 gas, an approximate 87% reduction." width="900" />
  <figcaption>
    <strong>Gas Cost: Fully On-Chain vs Semi-On-Chain.</strong>
    Fully on-chain aggregation consumes much more gas because aggregation logic and data handling are executed in smart contracts. Semi-on-chain FL keeps only trust-critical metadata on-chain while offloading bulk computation, reducing gas from 1,500,000 to 120,000 per round (about 87% lower), which is substantially more cost-efficient.
  </figcaption>
</figure>

<figure>
  <img src="docs/images/latency-comparison.png" alt="Box plot comparing round completion time: Fully On-Chain mean latency is about 12.1 seconds and Semi-On-Chain mean latency is about 3.4 seconds, around 72% lower." width="900" />
  <figcaption>
    <strong>Round Completion Latency Comparison.</strong>
    Fully on-chain training introduces higher round latency due to contract execution and block confirmation waits. Semi-on-chain FL reduces synchronization overhead and shortens round time from a mean of about 12.1s to about 3.4s (roughly 72% reduction), improving training throughput and responsiveness.
  </figcaption>
</figure>

## Notes and Caveats

- `expected_clients` variable exists in server but is not currently enforced.
- Aggregation is manual (`POST /aggregate`), not automatic when all clients submit.
- Contract ABI and address are duplicated between files; drift can break runtime behavior.
- `backend/blockchain_connect.py` appears experimental and currently contains invalid Python literals (`false` instead of `False`) if executed.

## Troubleshooting

- `Blockchain connected: False`
  - Verify Ganache is running on `127.0.0.1:7545`.

- `Not authorized` when penalizing
  - Contract owner does not match server default account.
  - Redeploy from matching account or update server account selection.

- `ModuleNotFoundError` for client scripts
  - Run clients as modules (`python -m backend.clients.client1`) from repo root.

- `Already registered`
  - Expected if same account registers multiple times.

- No aggregation effect
  - Ensure at least one valid update accepted before calling `/aggregate`.

## Suggested Improvements

- Move ABI and contract address into a shared config file or `.env`.
- Add hash verification on server (compare received weights hash vs on-chain hash).
- Add authentication/signatures for client identity.
- Replace static anomaly threshold with adaptive or robust aggregation.
- Add tests for server endpoints and contract integration.
- Add Docker Compose for one-command local startup.

## License

No license file is currently present in this repository.
-->
