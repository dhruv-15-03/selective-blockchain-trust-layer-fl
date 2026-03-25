import csv
from pathlib import Path
from typing import Tuple, List, Optional

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = REPO_ROOT / "data" / "transactions.csv"


LABEL_CANDIDATES = [
    "is_fraud",
    "fraud",
    "label",
    "target",
    "class",
    "y",
]


def _detect_label_col(fieldnames: List[str], row_sample: List[dict]) -> Optional[str]:
    for cand in LABEL_CANDIDATES:
        if cand in fieldnames:
            # Validate it looks like binary numeric in the sample.
            ok = 0
            total = 0
            for r in row_sample:
                v = r.get(cand)
                if v is None or v == "":
                    continue
                total += 1
                try:
                    fv = float(v)
                    # accept {0,1} with some tolerance
                    if abs(fv - 0.0) < 1e-9 or abs(fv - 1.0) < 1e-9:
                        ok += 1
                except Exception:
                    pass
            if total > 0 and ok / total >= 0.8:
                return cand
    return None


def _infer_numeric_feature_cols(fieldnames: List[str], row_sample: List[dict], label_col: str) -> List[str]:
    feature_cols: List[str] = []
    for col in fieldnames:
        if col == label_col:
            continue
        success = 0
        total = 0
        for r in row_sample:
            v = r.get(col)
            if v is None or v == "":
                continue
            total += 1
            try:
                float(v)
                success += 1
            except Exception:
                pass
        if total > 0 and success / total >= 0.8:
            feature_cols.append(col)
    return feature_cols


def infer_dataset_schema(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    max_rows_for_type: int = 2000,
) -> Tuple[List[str], str]:
    """
    Returns (feature_cols, label_col).
    Only infers numeric columns (float-convertible) for features.
    """
    if not dataset_path.exists():
        raise FileNotFoundError(str(dataset_path))

    with dataset_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows: List[dict] = []
        for i, r in enumerate(reader):
            rows.append(r)
            if i + 1 >= max_rows_for_type:
                break

    label_col = _detect_label_col(fieldnames, rows)
    if label_col is None:
        raise ValueError(
            "Could not infer label column. Expected one of: "
            + ", ".join(LABEL_CANDIDATES)
        )

    feature_cols = _infer_numeric_feature_cols(fieldnames, rows, label_col=label_col)
    if not feature_cols:
        raise ValueError("Could not infer any numeric feature columns.")

    return feature_cols, label_col


def load_dataset_scaled(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    label_col: Optional[str] = None,
    feature_cols: Optional[List[str]] = None,
) -> Tuple[np.ndarray, np.ndarray, List[str], str, np.ndarray, np.ndarray]:
    """
    Loads CSV, returns:
      X_scaled: (n, d)
      y: (n,)
      feature_cols: list of column names used
      label_col: label column name
      mean: (d,)
      std: (d,)
    """
    if not dataset_path.exists():
        raise FileNotFoundError(str(dataset_path))

    # Infer schema if not provided
    if label_col is None or feature_cols is None:
        inferred_feature_cols, inferred_label_col = infer_dataset_schema(dataset_path)
        feature_cols = inferred_feature_cols
        label_col = inferred_label_col

    assert feature_cols is not None
    assert label_col is not None

    X_rows: List[List[float]] = []
    y_rows: List[int] = []

    # First pass: parse all numeric rows
    with dataset_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                y_val = float(r.get(label_col, ""))
                if not (abs(y_val - 0.0) < 1e-9 or abs(y_val - 1.0) < 1e-9):
                    continue
                y_int = int(round(y_val))

                x_vec: List[float] = []
                ok = True
                for c in feature_cols:
                    v = r.get(c, "")
                    if v is None or v == "":
                        ok = False
                        break
                    x_vec.append(float(v))
                if not ok:
                    continue

                X_rows.append(x_vec)
                y_rows.append(y_int)
            except Exception:
                continue

    if len(X_rows) < 50:
        raise ValueError(f"Not enough usable rows found in {dataset_path}. Parsed: {len(X_rows)}")

    X = np.array(X_rows, dtype=float)
    y = np.array(y_rows, dtype=float)

    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std = np.where(std == 0.0, 1.0, std)
    X_scaled = (X - mean) / std

    return X_scaled, y, feature_cols, label_col, mean, std

