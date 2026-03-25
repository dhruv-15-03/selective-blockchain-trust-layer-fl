import csv
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]


INPUT_UPWORK_CSV_DEFAULT = REPO_ROOT / ".." / ".." / "Desktop" / "Upwork-Job-Scraper" / "execution" / "data" / "outputs" / "jobs" / "csv" / "job_results_20260320_115441.csv"
OUTPUT_DATASET_DEFAULT = REPO_ROOT / "data" / "transactions.csv"


FLOAT_FEATURES: List[str] = [
    "buyer_hire_rate_pct",
    "client_total_spent",
    "client_hires",
    "buyer_avgHourlyJobsRate_amount",
    "buyer_stats_hoursCount",
    "hourly_min",
    "hourly_max",
    "fixed_budget_amount",
    "duration",
    "level",
    "applicants",
    "numberOfPositionsToHire",
    "connects_required",
    "client_rating",
    "client_reviews",
    "buyer_stats_activeAssignmentsCount",
    "buyer_stats_totalJobsWithHires",
    "clientActivity_invitationsSent",
    "clientActivity_totalHired",
    "clientActivity_totalInvitedToInterview",
    "clientActivity_unansweredInvites",
    "buyer_jobs_openCount",
    "buyer_jobs_postedCount",
]

BOOL_FEATURES: List[str] = [
    "phone_verified",
    "isContractToHire",
    "payment_verified",
]


def parse_bool01(v: Optional[str]) -> Optional[int]:
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "y"):
        return 1
    if s in ("false", "0", "no", "n"):
        return 0
    return None


def parse_float(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except Exception:
        return None


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + float(np.exp(-x)))


def load_feature_distributions(csv_path: Path) -> Tuple[Dict[str, List[float]], Dict[str, List[int]]]:
    float_dist: Dict[str, List[float]] = {c: [] for c in FLOAT_FEATURES}
    bool_dist: Dict[str, List[int]] = {c: [] for c in BOOL_FEATURES}

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")

        for i, row in enumerate(reader):
            # Keep it fast: sample first ~50k rows
            if i >= 50000:
                break

            for c in FLOAT_FEATURES:
                if c not in row:
                    continue
                val = parse_float(row.get(c))
                if val is None:
                    continue
                float_dist[c].append(val)

            for c in BOOL_FEATURES:
                if c not in row:
                    continue
                b = parse_bool01(row.get(c))
                if b is None:
                    continue
                bool_dist[c].append(b)

    return float_dist, bool_dist


def make_feature_value(rng: np.random.Generator, name: str, float_dist: Dict[str, List[float]], bool_dist: Dict[str, List[int]]) -> float:
    if name in BOOL_FEATURES:
        dist = bool_dist.get(name, [])
        if not dist:
            # default: phone_verified often 1
            return 1.0 if name == "phone_verified" else 0.5
        # sample boolean and perturb not needed
        return float(rng.choice(dist))

    dist = float_dist.get(name, [])
    if not dist:
        # defaults for missing features (roughly Upwork-like)
        defaults = {
            "buyer_hire_rate_pct": (0.0, 100.0),
            "client_total_spent": (0.0, 5000.0),
            "client_hires": (0.0, 500.0),
            "buyer_avgHourlyJobsRate_amount": (5.0, 200.0),
            "buyer_stats_hoursCount": (0.0, 10000.0),
            "hourly_min": (0.0, 100.0),
            "hourly_max": (0.0, 200.0),
            "fixed_budget_amount": (0.0, 20000.0),
            "duration": (1.0, 365.0),
            "level": (0.0, 5.0),
            "applicants": (0.0, 500.0),
            "numberOfPositionsToHire": (1.0, 20.0),
            "connects_required": (0.0, 50.0),
            "client_rating": (0.0, 5.0),
            "client_reviews": (0.0, 1000.0),
            "buyer_stats_activeAssignmentsCount": (0.0, 50.0),
            "buyer_stats_totalJobsWithHires": (0.0, 200.0),
            "clientActivity_invitationsSent": (0.0, 5000.0),
            "clientActivity_totalHired": (0.0, 500.0),
            "clientActivity_totalInvitedToInterview": (0.0, 5000.0),
            "clientActivity_unansweredInvites": (0.0, 2000.0),
            "buyer_jobs_openCount": (0.0, 50.0),
            "buyer_jobs_postedCount": (0.0, 500.0),
        }
        lo, hi = defaults.get(name, (0.0, 1.0))
        return float(rng.uniform(lo, hi))

    base = float(rng.choice(dist))
    # Add modest noise; keep within plausible bounds
    noise_scale = 0.05 * (abs(base) + 1.0)
    val = base + float(rng.normal(0.0, noise_scale))

    # Clip some features to non-negative where appropriate
    if name not in ("client_rating", "level"):
        val = max(0.0, val)
    if name in ("client_rating",):
        val = float(np.clip(val, 0.0, 5.0))
    if name in ("level",):
        val = float(np.clip(val, 0.0, 5.0))

    return float(val)


def generate_dataset(n: int, seed: int, upwork_csv: Optional[Path], out_csv: Path) -> None:
    rng = np.random.default_rng(seed)
    random.seed(seed)

    if upwork_csv and upwork_csv.exists():
        float_dist, bool_dist = load_feature_distributions(upwork_csv)
        print(f"Loaded distributions from {upwork_csv}")
    else:
        float_dist, bool_dist = {}, {}
        print("No input CSV provided/found; using defaults.")

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    header = ["is_fraud"] + FLOAT_FEATURES + BOOL_FEATURES
    fraud_count = 0

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for _ in range(n):
            row: Dict[str, float] = {}

            for c in FLOAT_FEATURES:
                row[c] = make_feature_value(rng, c, float_dist, bool_dist)
            for c in BOOL_FEATURES:
                row[c] = make_feature_value(rng, c, float_dist, bool_dist)

            phone_verified = row["phone_verified"]
            payment_verified = row["payment_verified"]

            client_rating = row["client_rating"]
            client_reviews = row["client_reviews"]
            buyer_hire_rate_pct = row["buyer_hire_rate_pct"]
            unanswered = row["clientActivity_unansweredInvites"]
            invitations = row["clientActivity_invitationsSent"] + 1.0
            unanswered_ratio = unanswered / invitations

            # Simple fraud probability model (heuristic ground truth generator)
            # - Unverified phone/payment increases risk
            # - Low rating/reviews increases risk
            # - Very low hire rate increases risk
            # - High unanswered ratio increases risk
            fraud_score = (
                1.7 * (1.0 - phone_verified) +
                1.2 * (1.0 - payment_verified) +
                1.2 * max(0.0, (3.5 - client_rating) / 3.5) +
                0.9 * max(0.0, (5.0 - client_reviews) / 5.0) +
                0.8 * max(0.0, (25.0 - buyer_hire_rate_pct) / 25.0) +
                2.0 * max(0.0, unanswered_ratio)
            )

            p = sigmoid(1.5 * fraud_score - 3.0)
            is_fraud = 1 if rng.random() < p else 0

            fraud_count += is_fraud
            writer.writerow([is_fraud] + [row[c] for c in FLOAT_FEATURES] + [row[c] for c in BOOL_FEATURES])

    print(f"Wrote {n} samples to {out_csv}")
    print(f"Fraud rate: {fraud_count/n:.3f} ({fraud_count} / {n})")


if __name__ == "__main__":
    # Adjust these if you want a different input or output.
    input_csv = INPUT_UPWORK_CSV_DEFAULT
    output_csv = OUTPUT_DATASET_DEFAULT

    # Generate 10k samples as requested.
    generate_dataset(n=10000, seed=42, upwork_csv=input_csv, out_csv=output_csv)

