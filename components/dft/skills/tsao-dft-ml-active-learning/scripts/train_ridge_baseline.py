#!/usr/bin/env python3
"""Train a deterministic train-only standardized ridge baseline on grouped DFT data."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

import numpy as np

SOLVERS = ("auto", "primal", "dual")


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def metrics(y, prediction):
    y = np.asarray(y, dtype=float)
    prediction = np.asarray(prediction, dtype=float)
    if y.ndim != 1 or prediction.ndim != 1 or y.shape != prediction.shape or y.size == 0:
        raise ValueError("metrics require aligned non-empty one-dimensional arrays")
    if not np.isfinite(y).all() or not np.isfinite(prediction).all():
        raise ValueError("metric inputs must contain only finite values")
    error = prediction - y
    squared_error = float(error @ error)
    centered = y - y.mean()
    denominator = float(centered @ centered)
    mae = float(np.mean(np.abs(error)))
    rmse = math.sqrt(squared_error / y.size)
    r2 = float(1 - squared_error / denominator) if denominator > 0 else None
    return {"mae": mae, "rmse": rmse, "r2": r2}


def split_groups(rows, group, seed, frac_train=0.7, frac_valid=0.15):
    groups = sorted({row[group] for row in rows})
    rng = random.Random(seed)
    rng.shuffle(groups)
    count = len(groups)
    train_count = max(1, round(count * frac_train))
    valid_count = max(1, round(count * frac_valid)) if count >= 3 else 0
    if train_count + valid_count >= count:
        valid_count = max(0, count - train_count - 1)
    return {
        value: "train" if index < train_count else "valid" if index < train_count + valid_count else "test"
        for index, value in enumerate(groups)
    }


def fit_ridge(
    x_train: np.ndarray,
    y_train: np.ndarray,
    alpha: float,
    solver: str = "auto",
) -> tuple[float, np.ndarray, str, int]:
    """Fit ridge with an unpenalized intercept and the smaller linear system when possible."""

    x_train = np.asarray(x_train, dtype=float)
    y_train = np.asarray(y_train, dtype=float)
    if x_train.ndim != 2 or y_train.ndim != 1 or len(x_train) != len(y_train):
        raise ValueError("x_train must be 2-D and aligned with one-dimensional y_train")
    if not np.isfinite(x_train).all() or not np.isfinite(y_train).all():
        raise ValueError("training matrix and target must contain only finite values")
    if not np.isfinite(alpha) or alpha < 0:
        raise ValueError("alpha must be finite and non-negative")
    if solver not in SOLVERS:
        raise ValueError(f"solver must be one of {SOLVERS}")

    sample_count, feature_count = x_train.shape
    if sample_count < 1 or feature_count < 1:
        raise ValueError("x_train must contain at least one sample and one feature")

    if alpha == 0:
        design = np.column_stack((np.ones(sample_count), x_train))
        beta, *_ = np.linalg.lstsq(design, y_train, rcond=None)
        return float(beta[0]), np.asarray(beta[1:], float), "lstsq", min(design.shape)

    feature_mean = x_train.mean(axis=0)
    target_mean = float(y_train.mean())
    centered_features = x_train - feature_mean
    centered_target = y_train - target_mean

    selected = solver
    if solver == "auto":
        selected = "dual" if feature_count > sample_count else "primal"

    if selected == "dual":
        gram = centered_features @ centered_features.T
        gram.flat[:: sample_count + 1] += alpha
        dual = np.linalg.solve(gram, centered_target)
        coefficients = centered_features.T @ dual
        dimension = sample_count
    else:
        gram = centered_features.T @ centered_features
        gram.flat[:: feature_count + 1] += alpha
        right_hand_side = centered_features.T @ centered_target
        coefficients = np.linalg.solve(gram, right_hand_side)
        dimension = feature_count

    coefficients = np.asarray(coefficients, dtype=float)
    intercept = target_mean - float(feature_mean @ coefficients)
    return intercept, coefficients, selected, dimension


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--features", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--solver", choices=SOLVERS, default="auto")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    rows = read(args.dataset)
    features = [value.strip() for value in args.features.split(",") if value.strip()]
    errors = []
    if not rows:
        errors.append("dataset is empty")
    if not features:
        errors.append("at least one feature is required")
    if not math.isfinite(args.alpha) or args.alpha < 0:
        errors.append("alpha must be finite and non-negative")
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1

    try:
        feature_matrix = np.asarray([[float(row[feature]) for feature in features] for row in rows], dtype=float)
        target = np.asarray([float(row[args.target]) for row in rows], dtype=float)
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1

    assignment = split_groups(rows, args.group, args.seed)
    split_labels = np.asarray([assignment[row[args.group]] for row in rows])
    indices = {name: np.flatnonzero(split_labels == name) for name in ("train", "valid", "test")}
    if len(indices["train"]) < 2 or len(indices["test"]) < 1:
        print(json.dumps({"ok": False, "errors": ["insufficient grouped train/test samples"]}, indent=2))
        return 1

    if not np.isfinite(feature_matrix).all() or not np.isfinite(target).all():
        print(json.dumps({"ok": False, "errors": ["features and target must contain only finite values"]}, indent=2))
        return 1

    train_index = indices["train"]
    mean = feature_matrix[train_index].mean(axis=0)
    std = feature_matrix[train_index].std(axis=0)
    constant_mask = std == 0
    constant_features = [feature for feature, constant in zip(features, constant_mask, strict=True) if constant]
    std[constant_mask] = 1.0
    standardized = (feature_matrix - mean) / std

    try:
        intercept, coefficients, solver_used, solve_dimension = fit_ridge(
            standardized[train_index],
            target[train_index],
            args.alpha,
            args.solver,
        )
    except (ValueError, np.linalg.LinAlgError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1

    prediction = intercept + standardized @ coefficients
    beta = np.concatenate(([intercept], coefficients))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = [*list(rows[0]), "split", "prediction", "residual"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(rows):
            writer.writerow(
                {
                    **row,
                    "split": split_labels[index],
                    "prediction": prediction[index],
                    "residual": prediction[index] - target[index],
                }
            )

    card = {
        "schema_version": "1.1",
        "model_id": "ridge-baseline",
        "model_family": "ridge",
        "features": features,
        "target": args.target,
        "group_column": args.group,
        "split_policy": "group",
        "seed": args.seed,
        "alpha": args.alpha,
        "solver_requested": args.solver,
        "solver_used": solver_used,
        "solve_dimension": solve_dimension,
        "data_shape": {"samples": len(rows), "features": len(features), "training_samples": len(train_index)},
        "constant_features": constant_features,
        "preprocessing_fit_scope": "train_only",
        "standardization": {"mean": mean.tolist(), "std": std.tolist()},
        "coefficients": beta.tolist(),
        "metrics": {name: metrics(target[index], prediction[index]) for name, index in indices.items() if len(index)},
        "counts": {name: len(index) for name, index in indices.items()},
        "scientific_interpretation": "baseline_only",
        "status": "validated",
    }
    (args.out_dir / "model-card.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "outputs": [str(args.out_dir / "predictions.csv"), str(args.out_dir / "model-card.json")],
                "solver_used": solver_used,
                "solve_dimension": solve_dimension,
                "metrics": card["metrics"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
