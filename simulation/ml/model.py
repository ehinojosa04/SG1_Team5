"""
SolarModel — inference wrapper for the trained Green Grid ML model.

Loads pre-trained coefficients from model_coefficients.json and exposes
a single predict() method that converts real weather features into an
estimated solar generation value in Watts for a 5 kW panel system.

Usage:
    from ml.model import SolarModel

    model = SolarModel()           # uses default path
    watts = model.predict(
        ghi=650.0,                 # W/m²
        temperature=22.0,          # °C
        humidity=45.0,             # %
        zenith=35.0,               # degrees
        cloud_type=1,              # NSRDB cloud type code (0–12)
        clearsky_ghi=800.0,        # W/m²
    )
"""

import json
import os


class SolarModel:
    """Inference-only wrapper around a trained linear (or polynomial) model.

    The model was trained on the NSRDB 2006 San Francisco dataset and predicts
    distributed PV power for a 33 MW system.  The result is scaled down to
    match the simulated 5 kW rooftop panel.
    """

    _DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'model_coefficients.json')

    def __init__(self, coefficients_path=None):
        path = coefficients_path or self._DEFAULT_PATH

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Model coefficients not found at {path}.\n"
                "Please run  python ml/train.py  first."
            )

        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        self.features      = data['features']          # ordered feature list
        self.weights       = data['weights']           # one weight per feature
        self.bias          = data['bias']              # intercept
        self.means         = data['feature_means']     # normalisation mean
        self.stds          = data['feature_stds']      # normalisation std
        self.is_poly       = data.get('is_polynomial', False)
        self.system_peak_w = data.get('system_peak_w', 33_000_000)
        self.panel_peak_w  = data.get('panel_peak_w',  5_000)

        # Fraction of system output that corresponds to our panel
        self._scale = self.panel_peak_w / self.system_peak_w  # dimensionless

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalise(self, raw_values):
        """Z-score normalise a list of raw feature values."""
        return [
            (raw_values[i] - self.means[self.features[i]])
            / self.stds[self.features[i]]
            for i in range(len(self.features))
        ]

    @staticmethod
    def _expand_poly(x):
        """Append squared terms for polynomial mode."""
        return list(x) + [xi ** 2 for xi in x]

    def _raw_predict(self, x_norm):
        """Dot product w·x + b.  x_norm must already be normalised."""
        return self.bias + sum(
            self.weights[j] * x_norm[j] for j in range(len(self.weights))
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, ghi, temperature, humidity, zenith,
                cloud_type, clearsky_ghi):
        """Predict solar generation in Watts for the 5 kW panel system.

        Parameters
        ----------
        ghi          : float — Global Horizontal Irradiance  (W/m²)
        temperature  : float — Air temperature               (°C)
        humidity     : float — Relative humidity             (%)
        zenith       : float — Solar zenith angle            (degrees)
        cloud_type   : float — NSRDB cloud-type code         (0–12)
        clearsky_ghi : float — Clear-sky GHI                 (W/m²)

        Returns
        -------
        float — Estimated generation in Watts (≥ 0).
        """
        # The order MUST match the FEATURES list used during training:
        # ['GHI', 'Temperature', 'Relative Humidity',
        #  'Solar Zenith Angle', 'Cloud Type', 'Clearsky GHI']
        raw = [ghi, temperature, humidity, zenith, cloud_type, clearsky_ghi]
        x_norm = self._normalise(raw)

        if self.is_poly:
            x_norm = self._expand_poly(x_norm)

        # Prediction is in MW (same units as the training target)
        pred_mw = self._raw_predict(x_norm)

        # Scale to the 5 kW panel and convert MW → W
        watts = max(0.0, pred_mw * self._scale * 1_000_000)
        return watts
