"""
Train the Green Grid solar generation model from the canonical ML dataset.

The MVP model is a from-scratch linear regression that predicts actual solar
``capacity_factor`` from shifted weather + time features.

Run from the simulation/ directory:
    python ml/train.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parents[1]
if str(SIM_DIR) not in sys.path:
    sys.path.insert(0, str(SIM_DIR))

import config
from ml import prepare_data
from ml.linear_regression import LinearRegression

COEFFICIENTS_FILE = Path(__file__).resolve().parent / "model_coefficients.json"
LINEAR_ITERATIONS = 600
LINEAR_LEARNING_RATE = 0.05


def z_score_params(rows, features):
    """Compute feature means/stds from training rows only."""
    means, stds = {}, {}
    for feature in features:
        values = [float(row[feature]) for row in rows]
        mean = sum(values) / len(values)
        std = math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
        means[feature] = mean
        stds[feature] = std if std > 1e-9 else 1.0
    return means, stds


def normalise(rows, features, means, stds):
    return [
        [(float(row[feature]) - means[feature]) / stds[feature] for feature in features]
        for row in rows
    ]


def target_values(rows):
    return [float(row[prepare_data.TARGET_COLUMN]) for row in rows]


def metric_values(model, X, y):
    predictions = model.predict_batch(X)
    n = len(y)
    mse = sum((predictions[i] - y[i]) ** 2 for i in range(n)) / n
    mae = sum(abs(predictions[i] - y[i]) for i in range(n)) / n
    mean_y = sum(y) / n
    ss_res = sum((y[i] - predictions[i]) ** 2 for i in range(n))
    ss_tot = sum((y[i] - mean_y) ** 2 for i in range(n))
    return {
        "mse": mse,
        "mae": mae,
        "rmse": math.sqrt(mse),
        "r2": 1.0 - ss_res / ss_tot if ss_tot else 0.0,
    }


def print_metrics(model_name, metrics_by_split):
    print(f"\n  {model_name}")
    for split_name in ["train", "validation", "test"]:
        metrics = metrics_by_split[split_name]
        print(
            f"    {split_name:<10} "
            f"MSE={metrics['mse']:.6f}  "
            f"MAE={metrics['mae']:.6f}  "
            f"RMSE={metrics['rmse']:.6f}  "
            f"R2={metrics['r2']:.4f}"
        )


def rows_by_split(df, features):
    cols = [*features, prepare_data.TARGET_COLUMN, "split"]
    records = df[cols].to_dict("records")
    return {
        split_name: [row for row in records if row["split"] == split_name]
        for split_name in ["train", "validation", "test"]
    }


def evaluate_model(model, X_by_split, y_by_split):
    return {
        split_name: metric_values(model, X_by_split[split_name], y_by_split[split_name])
        for split_name in ["train", "validation", "test"]
    }


def main():
    print("\n[1/4] Building validated 15-minute dataset ...")
    df = prepare_data.build_dataset(prepare_data.DEFAULT_VARIANT)
    congruence = prepare_data.validate_dataset(df, prepare_data.DEFAULT_VARIANT)
    feature_group = config.ML_ACTIVE_FEATURE_GROUP
    features = prepare_data.feature_columns(df, feature_group)
    cloud_cols = prepare_data.cloud_type_columns(df)

    print(f"      Rows: {len(df):,}")
    print(f"      Target: {prepare_data.TARGET_COLUMN}")
    print(f"      Feature group: {feature_group} ({len(features)} expanded features)")
    print(f"      Actual/GHI correlation: {congruence['actual_ghi_correlation']:.4f}")

    print("\n[2/4] Splitting by prepared chronological labels ...")
    split_rows = rows_by_split(df, features)
    for split_name, rows in split_rows.items():
        print(f"      {split_name:<10} {len(rows):,} rows")

    print("\n[3/4] Normalising from train split only ...")
    means, stds = z_score_params(split_rows["train"], features)
    X_by_split = {
        split_name: normalise(rows, features, means, stds)
        for split_name, rows in split_rows.items()
    }
    y_by_split = {split_name: target_values(rows) for split_name, rows in split_rows.items()}

    print("\n[4/4] Training from-scratch linear regression ...")
    linear = LinearRegression()
    linear.fit(
        X_by_split["train"],
        y_by_split["train"],
        learning_rate=LINEAR_LEARNING_RATE,
        iterations=LINEAR_ITERATIONS,
        log_every=150,
        verbose=True,
    )

    print("\nEvaluating model ...")
    linear_metrics = evaluate_model(linear, X_by_split, y_by_split)
    print_metrics("LinearRegression", linear_metrics)

    payload = {
        "model_type": "LinearRegression",
        "is_polynomial": False,
        "target": prepare_data.TARGET_COLUMN,
        "feature_group": feature_group,
        "features": features,
        "cloud_type_columns": cloud_cols,
        "weights": linear.weights,
        "bias": linear.bias,
        "feature_means": means,
        "feature_stds": stds,
        "site_capacity_mw": config.ML_SITE_CAPACITY_MW,
        "weather_time_shift_hours": config.ML_WEATHER_TIME_SHIFT_HOURS,
        "training_variant": prepare_data.DEFAULT_VARIANT,
        "hyperparameters": {
            "learning_rate": LINEAR_LEARNING_RATE,
            "iterations": LINEAR_ITERATIONS,
        },
        "metrics": linear_metrics,
    }

    with open(COEFFICIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    print(f"\n  Active linear model saved -> {COEFFICIENTS_FILE}")


if __name__ == "__main__":
    main()
