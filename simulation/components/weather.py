"""
Weather component for the Green Grid Digital Twin.

When available, this component exposes the same shifted 15-minute NSRDB
weather/time features used by ``ml/prepare_data.py`` and ``ml/train.py``.
If the real-data lookup cannot be built, it falls back to the original
season-aware stochastic weather model.
"""

from __future__ import annotations

import math
import random
from datetime import datetime

from simpy import Environment

from config import CLOUD_COVERAGE, SEASON_PROBABILITY_FACTOR, WEATHER_TYPES


_CLOUD_TYPE_TO_COVERAGE = {
    0: 0.00,
    1: 0.10,
    2: 0.80,
    3: 0.50,
    4: 0.60,
    5: 0.65,
    6: 0.70,
    7: 0.40,
    8: 0.55,
    9: 0.75,
    10: 0.50,
    11: 0.85,
    12: 0.90,
}


class Weather:
    def __init__(self, env: Environment):
        self.env = env
        self.cloud_coverage = 0.0
        self.cloud_type = 0
        self.temperature = 20.0
        self.humidity = 50.0
        self.zenith = 45.0
        self.dhi = 0.0
        self.dni = 0.0
        self.ghi = 0.0
        self.wind_speed = 0.0
        self.pressure = 1013.0
        self.clearsky_ghi = 0.0
        self.weather = "CLEAR"
        self.ml_features: dict[str, float] = {}

        self._lookup = self._load_weather_data()

    def _load_weather_data(self):
        try:
            from ml.prepare_data import build_weather_feature_lookup

            lookup = build_weather_feature_lookup()
            print(
                f"[Weather] Loaded {len(lookup)} shifted 15-minute weather entries "
                "from the prepared ML dataset."
            )
            return lookup
        except FileNotFoundError as exc:
            print(f"[Weather] WARNING: {exc}. Using synthetic weather model.")
        except Exception as exc:
            print(f"[Weather] WARNING: Could not load ML weather data ({exc}). "
                  "Using synthetic weather model.")
        return {}

    def update(self, date: datetime):
        key = (date.month, date.day, date.hour, date.minute)

        if key in self._lookup:
            self._apply_real_entry(self._lookup[key])
        else:
            self._stochastic_update(date)

    def _apply_real_entry(self, entry: dict):
        self.temperature = entry["temperature_c"]
        self.humidity = entry["relative_humidity_pct"]
        self.dhi = entry["dhi"]
        self.dni = entry["dni"]
        self.ghi = entry["ghi"]
        self.zenith = entry["solar_zenith_angle"]
        self.wind_speed = entry["wind_speed"]
        self.pressure = entry["pressure"]
        self.cloud_type = entry["cloud_type"]
        self.clearsky_ghi = max(self.ghi, self.dhi)
        self.cloud_coverage = _CLOUD_TYPE_TO_COVERAGE.get(self.cloud_type, 0.5)
        self.weather = _coverage_label(self.cloud_coverage)
        self.ml_features = dict(entry["features"])

    def _stochastic_update(self, date: datetime):
        month = date.month
        season = (
            "WINTER" if month in (12, 1, 2)
            else "SPRING" if month in (3, 4, 5)
            else "SUMMER" if month in (6, 7, 8)
            else "FALL"
        )

        self.weather = random.choices(
            population=WEATHER_TYPES,
            weights=SEASON_PROBABILITY_FACTOR[season],
            k=1,
        )[0]
        lo, hi = CLOUD_COVERAGE[self.weather]
        self.cloud_coverage = random.uniform(lo, hi)
        self.cloud_type = int(self.cloud_coverage * 12)
        self.temperature = 20.0
        self.humidity = 50.0
        self.zenith = 45.0
        self.dhi = 0.0
        self.dni = max(0.0, 600.0 * (1 - self.cloud_coverage))
        self.ghi = self.dni
        self.wind_speed = 0.0
        self.pressure = 1013.0
        self.clearsky_ghi = 700.0
        self.ml_features = self._stochastic_features(date)

    def _stochastic_features(self, date: datetime) -> dict[str, float]:
        hour_decimal = date.hour + date.minute / 60
        day_of_year = date.timetuple().tm_yday
        features = {
            "temperature_c": self.temperature,
            "relative_humidity_pct": self.humidity,
            "dhi": self.dhi,
            "dni": self.dni,
            "ghi": self.ghi,
            "solar_zenith_angle": self.zenith,
            "wind_speed": self.wind_speed,
            "pressure": self.pressure,
            "hour_sin": math.sin(2 * math.pi * hour_decimal / 24),
            "hour_cos": math.cos(2 * math.pi * hour_decimal / 24),
            "day_sin": math.sin(2 * math.pi * day_of_year / 365),
            "day_cos": math.cos(2 * math.pi * day_of_year / 365),
            f"cloud_type_{self.cloud_type}": 1.0,
        }
        return features


def _coverage_label(coverage: float) -> str:
    if coverage < 0.15:
        return "CLEAR"
    if coverage < 0.45:
        return "PARTLY_CLOUDY"
    if coverage < 0.75:
        return "MOSTLY_CLOUDY"
    return "OVERCAST"
