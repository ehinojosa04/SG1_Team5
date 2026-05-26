"""
Training script for the Green Grid solar generation ML model.

Steps performed:
  1. Load and clean the NSRDB dataset via data_prep.py
  2. Z-score normalise all features (saves means/stds to JSON)
  3. Split chronologically: 80% train / 20% test
  4. Train LinearRegression and PolynomialRegression (both from scratch)
  5. Print a side-by-side metrics comparison (MSE, MAE, RMSE, R²)
  6. Save the best model's coefficients to model_coefficients.json

Run from the simulation/ directory:
    python ml/train.py
"""

import csv
import json
import math
import os
import sys

# Allow imports from simulation/ regardless of CWD
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.data_prep           import load_and_prepare, print_data_dictionary
from ml.linear_regression   import LinearRegression
from ml.polynomial_regression import PolynomialRegression

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ML_DIR           = os.path.dirname(os.path.abspath(__file__))
COEFFICIENTS_FILE = os.path.join(_ML_DIR, 'model_coefficients.json')

FEATURES = ['GHI', 'Temperature', 'Relative Humidity',
            'Solar Zenith Angle', 'Cloud Type', 'Clearsky GHI']
TARGET   = 'Power_MW'

# Scaling: the DPV dataset represents a 33 MW system; our panel is 5 kW.
SYSTEM_PEAK_W = 33_000_000   # 33 MW in watts
PANEL_PEAK_W  = 5_000        # 5 kW


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def z_score_params(data, features):
    """Compute mean and std for each feature column."""
    means, stds = {}, {}
    for f in features:
        vals  = [row[f] for row in data]
        mean  = sum(vals) / len(vals)
        std   = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
        means[f] = mean
        stds[f]  = std if std > 1e-9 else 1.0
    return means, stds


def normalise(data, features, means, stds):
    """Return a list of normalised feature vectors (list of lists)."""
    X = []
    for row in data:
        X.append([(row[f] - means[f]) / stds[f] for f in features])
    return X


# ---------------------------------------------------------------------------
# Train / test split (chronological – no shuffling)
# ---------------------------------------------------------------------------

def split(X, y, test_ratio=0.2):
    n     = len(X)
    split = int(n * (1.0 - test_ratio))
    return X[:split], X[split:], y[:split], y[split:]


# ---------------------------------------------------------------------------
# Metrics table printer
# ---------------------------------------------------------------------------

def print_metrics(name, model, X_test, y_test):
    mse  = model.mse(X_test,  y_test)
    mae  = model.mae(X_test,  y_test)
    rmse = model.rmse(X_test, y_test)
    r2   = model.r2(X_test,   y_test)
    print(f"  {name:<25}  MSE={mse:>9.5f}  MAE={mae:>8.5f}  "
          f"RMSE={rmse:>8.5f}  R²={r2:>7.4f}")
    return {'mse': mse, 'mae': mae, 'rmse': rmse, 'r2': r2}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # ── 1. Load data ──────────────────────────────────────────────────────
    print("\n[1/5] Loading and preparing dataset …")
    data = load_and_prepare(verbose=False)
    print_data_dictionary(data)
    print(f"      Total daytime samples: {len(data)}")

    # ── 2. Normalise features ─────────────────────────────────────────────
    print("\n[2/5] Normalising features (z-score) …")
    means, stds = z_score_params(data, FEATURES)
    for f in FEATURES:
        print(f"  {f:<28}  μ={means[f]:>8.3f}  σ={stds[f]:>8.3f}")

    X_norm = normalise(data, FEATURES, means, stds)
    y      = [row[TARGET] for row in data]

    # ── 3. Split ──────────────────────────────────────────────────────────
    print("\n[3/5] Splitting chronologically (80 % train / 20 % test) …")
    X_tr, X_te, y_tr, y_te = split(X_norm, y)
    print(f"      Train: {len(X_tr)} samples   Test: {len(X_te)} samples")

    # ── 4. Train both models ──────────────────────────────────────────────
    print("\n[4/5] Training models …")

    print("\n  ── Linear Regression (gradient descent) ──")
    lr = LinearRegression()
    lr.fit(X_tr, y_tr, learning_rate=0.05, iterations=2000,
           log_every=400, verbose=True)

    print("\n  ── Polynomial Regression (degree-2 features) ──")
    pr = PolynomialRegression()
    pr.fit(X_tr, y_tr, learning_rate=0.005, iterations=2000,
           log_every=400, verbose=True)

    # ── 5. Evaluate and compare ───────────────────────────────────────────
    print("\n[5/5] Model comparison on hold-out test set:")
    print("-" * 75)
    lr_metrics = print_metrics("LinearRegression",    lr, X_te, y_te)
    pr_metrics = print_metrics("PolynomialRegression", pr, X_te, y_te)
    print("-" * 75)

    # Pick the model with the higher R²
    if lr_metrics['r2'] >= pr_metrics['r2']:
        best_model   = lr
        best_name    = "LinearRegression"
        best_metrics = lr_metrics
        is_poly      = False
        best_weights = lr.weights
        best_bias    = lr.bias
    else:
        best_model   = pr
        best_name    = "PolynomialRegression"
        best_metrics = pr_metrics
        is_poly      = True
        best_weights = pr.weights
        best_bias    = pr.bias

    print(f"\n  Winner: {best_name}  (R²={best_metrics['r2']:.4f})")

    # ── Save coefficients ─────────────────────────────────────────────────
    payload = {
        'model_type':      best_name,
        'is_polynomial':   is_poly,
        'features':        FEATURES,
        'weights':         best_weights,
        'bias':            best_bias,
        'feature_means':   means,
        'feature_stds':    stds,
        'system_peak_w':   SYSTEM_PEAK_W,
        'panel_peak_w':    PANEL_PEAK_W,
        'metrics': {
            'mse':  best_metrics['mse'],
            'mae':  best_metrics['mae'],
            'rmse': best_metrics['rmse'],
            'r2':   best_metrics['r2'],
        }
    }

    with open(COEFFICIENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)

    print(f"\n  Coefficients saved → {COEFFICIENTS_FILE}")
    print("  Run python3 simulation.py to start the neighborhood simulation with the ML model.\n")


if __name__ == '__main__':
    main()
