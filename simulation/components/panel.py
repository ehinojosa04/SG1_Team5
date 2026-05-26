"""
Solar Panel component for the Green Grid Digital Twin.

Uses a trained gradient-descent ML model (SolarModel) when SOLAR_MODEL_MODE
is "ml", otherwise falls back to the original sinusoidal model.

Generation is returned in kW (instantaneous power) to match the neighborhood
simulator's HouseUnit.stepUpdate() contract.
"""

import math
from simpy import Environment

from components.battery import Battery
from components.weather import Weather
from config import SOLAR_PEAK, SOLAR_MODEL_MODE, GRADIENT_ML_MODEL_PATH


class Panel:
    def __init__(self, env: Environment, battery: Battery, weather: Weather,
                 peak_kw: float = SOLAR_PEAK, enabled: bool = True):
        self.env = env
        self.battery = battery
        self.weather = weather
        self.peak_kw = peak_kw if enabled else 0.0
        self.enabled = bool(enabled) and peak_kw > 0
        self.generation = 0.0
        self._model = self._load_model() if SOLAR_MODEL_MODE == "ml" else None

    def _load_model(self):
        """Try to load the trained SolarModel; return None on failure."""
        try:
            from ml.model import SolarModel
            model = SolarModel(GRADIENT_ML_MODEL_PATH)
            return model
        except FileNotFoundError as e:
            print(f"[Panel] WARNING: {e}")
            print("[Panel] Falling back to sinusoidal generation model.")
            return None
        except Exception as e:
            print(f"[Panel] WARNING: Could not load ML model ({e}). "
                  "Falling back to sinusoidal model.")
            return None

    def update(self, hour: float | None = None):
        """Compute solar generation in kW for the current tick."""
        if not self.enabled:
            self.generation = 0.0
            return

        if self._model is not None:
            raw_watts = self._model.predict(
                ghi=self.weather.ghi,
                temperature=self.weather.temperature,
                humidity=self.weather.humidity,
                zenith=self.weather.zenith,
                cloud_type=self.weather.cloud_type,
                clearsky_ghi=self.weather.clearsky_ghi,
            )
            # Model is calibrated for a 5 kW reference panel; scale to this house.
            reference_kw = 5.0
            self.generation = max(0.0, (raw_watts / 1000.0) * (self.peak_kw / reference_kw))
        else:
            tick_hour = hour if hour is not None else (self.env.now % 24)
            sun_angle = (tick_hour - 6) * (math.pi / 12)
            self.generation = max(
                0.0,
                self.peak_kw * math.sin(sun_angle) * (1 - self.weather.cloud_coverage),
            )
