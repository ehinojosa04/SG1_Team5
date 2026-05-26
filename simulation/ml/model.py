"""
Inference wrapper for the trained Green Grid solar model.

The model predicts normalized solar output (capacity_factor) and then scales it
to each household's installed PV capacity.
"""

from __future__ import annotations

import json
import os


class SolarModel:
    _DEFAULT_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "model_coefficients.json",
    )

    def __init__(self, coefficients_path=None):
        path = coefficients_path or self._DEFAULT_PATH

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Model coefficients not found at {path}.\n"
                "Please run python ml/train.py first."
            )

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self.model_type = data.get("model_type", "LinearRegression")
        self.target = data.get("target", "Power_MW")
        self.feature_group = data.get("feature_group")
        self.features = data["features"]
        self.weights = data["weights"]
        self.bias = data["bias"]
        self.means = data["feature_means"]
        self.stds = data["feature_stds"]
        self.site_capacity_mw = data.get(
            "site_capacity_mw",
            data.get("system_peak_w", 33_000_000) / 1_000_000,
        )

    def _normalise(self, raw_values):
        return [
            (raw_values[i] - self.means[self.features[i]]) / self.stds[self.features[i]]
            for i in range(len(self.features))
        ]

    def _raw_predict(self, values):
        return self.bias + sum(
            self.weights[index] * values[index]
            for index in range(len(self.weights))
        )

    def _feature_values(self, features: dict) -> list[float]:
        return [float(features.get(feature, 0.0)) for feature in self.features]

    def predict_capacity_factor(self, features: dict) -> float:
        """Predict a capacity factor clamped to the physical [0, 1] range."""
        if float(features.get("ghi", features.get("GHI", 0.0))) <= 1.0:
            return 0.0

        values = self._normalise(self._feature_values(features))
        prediction = self._raw_predict(values)
        if self.target != "capacity_factor":
            prediction = prediction / self.site_capacity_mw

        return max(0.0, min(1.0, prediction))

    def predict_kw(self, features: dict, peak_kw: float) -> float:
        """Predict instantaneous PV generation in kW for a household."""
        if peak_kw <= 0:
            return 0.0
        return self.predict_capacity_factor(features) * peak_kw

    def predict(self, ghi, temperature, humidity, zenith, cloud_type, clearsky_ghi):
        """Backward-compatible wrapper returning watts for a 5 kW reference panel."""
        features = {
            "ghi": ghi,
            "GHI": ghi,
            "temperature_c": temperature,
            "Temperature": temperature,
            "relative_humidity_pct": humidity,
            "Relative Humidity": humidity,
            "solar_zenith_angle": zenith,
            "Solar Zenith Angle": zenith,
            "cloud_type": cloud_type,
            "Cloud Type": cloud_type,
            "clearsky_ghi": clearsky_ghi,
            "Clearsky GHI": clearsky_ghi,
            f"cloud_type_{int(round(cloud_type))}": 1.0,
        }
        return self.predict_kw(features, 5.0) * 1000.0
