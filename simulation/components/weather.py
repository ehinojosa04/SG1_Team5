"""
Weather component for the Green Grid Digital Twin.

On initialisation the component reads the NSRDB 2006 San Francisco 30-minute
weather CSV and builds an in-memory lookup keyed by (month, day, hour).

Each simulation tick, update(date) looks up the real weather entry for that
calendar month/day/hour (ignoring year, so 2026 dates map to 2006 data) and
exposes the following attributes for use by Panel and the simulation log:

    cloud_coverage  – float  [0, 1]  proxy derived from Cloud Type
    cloud_type      – int    [0, 12] NSRDB cloud type code
    temperature     – float  °C
    humidity        – float  %  (Relative Humidity)
    zenith          – float  degrees (Solar Zenith Angle)
    ghi             – float  W/m²  (Global Horizontal Irradiance)
    clearsky_ghi    – float  W/m²  (Clearsky GHI)
    weather         – str    label (kept for logging compatibility)

If the real-data lookup fails (missing entry or file not found) the component
falls back to the original season-aware stochastic model.
"""

import csv
import os
import random
from datetime import datetime

from simpy import Environment
from config import SEASON_PROBABILITY_FACTOR, CLOUD_COVERAGE, WEATHER_TYPES, ML_DATA_DIR

# NSRDB cloud type codes → approximate cloud-coverage fraction [0, 1]
_CLOUD_TYPE_TO_COVERAGE = {
    0:  0.00,
    1:  0.10,
    2:  0.80,
    3:  0.50,
    4:  0.60,
    5:  0.65,
    6:  0.70,
    7:  0.40,
    8:  0.55,
    9:  0.75,
    10: 0.50,
    11: 0.85,
    12: 0.90,
}


class Weather:
    def __init__(self, env: Environment):
        self.env            = env
        self.cloud_coverage = 0.0
        self.cloud_type     = 0
        self.temperature    = 20.0
        self.humidity       = 50.0
        self.zenith         = 45.0
        self.ghi            = 0.0
        self.clearsky_ghi   = 0.0
        self.weather        = "CLEAR"

        self._lookup = self._load_weather_data()

    def _load_weather_data(self):
        """Read 137337_Weather_30m.csv, aggregate to hourly, build lookup."""
        weather_file = os.path.join(ML_DATA_DIR, "137337_Weather_30m.csv")
        lookup = {}

        try:
            accum = {}
            with open(weather_file, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)
                next(reader)
                header = next(reader)

                for row in reader:
                    d = dict(zip(header, row))
                    try:
                        key = (int(d["Month"]), int(d["Day"]), int(d["Hour"]))
                        if key not in accum:
                            accum[key] = {
                                "GHI": 0.0, "Temperature": 0.0,
                                "Relative Humidity": 0.0,
                                "Solar Zenith Angle": 0.0,
                                "Cloud Type": 0.0, "Clearsky GHI": 0.0,
                                "_n": 0,
                            }
                        a = accum[key]
                        a["GHI"]               += float(d["GHI"])
                        a["Temperature"]        += float(d["Temperature"])
                        a["Relative Humidity"]  += float(d["Relative Humidity"])
                        a["Solar Zenith Angle"] += float(d["Solar Zenith Angle"])
                        a["Cloud Type"]         += float(d["Cloud Type"])
                        a["Clearsky GHI"]       += float(d["Clearsky GHI"])
                        a["_n"]                 += 1
                    except (ValueError, KeyError):
                        continue

            for key, a in accum.items():
                n = a["_n"]
                if n == 0:
                    continue
                ct = int(round(a["Cloud Type"] / n))
                lookup[key] = {
                    "ghi":            a["GHI"] / n,
                    "temperature":    a["Temperature"] / n,
                    "humidity":       a["Relative Humidity"] / n,
                    "zenith":         a["Solar Zenith Angle"] / n,
                    "cloud_type":     ct,
                    "clearsky_ghi":   a["Clearsky GHI"] / n,
                    "cloud_coverage": _CLOUD_TYPE_TO_COVERAGE.get(ct, 0.5),
                }

            print(f"[Weather] Loaded {len(lookup)} real hourly entries "
                  f"from NSRDB 2006 dataset.")
        except FileNotFoundError:
            print(f"[Weather] WARNING: {weather_file} not found. "
                  "Using synthetic weather model.")
        except Exception as e:
            print(f"[Weather] WARNING: Could not load weather data ({e}). "
                  "Using synthetic weather model.")

        return lookup

    def update(self, date: datetime):
        """Update weather state for the given simulation timestamp."""
        key = (date.month, date.day, date.hour)

        if key in self._lookup:
            entry = self._lookup[key]
            self.ghi            = entry["ghi"]
            self.temperature    = entry["temperature"]
            self.humidity       = entry["humidity"]
            self.zenith         = entry["zenith"]
            self.cloud_type     = entry["cloud_type"]
            self.clearsky_ghi   = entry["clearsky_ghi"]
            self.cloud_coverage = entry["cloud_coverage"]
            self.weather = _coverage_label(self.cloud_coverage)
        else:
            self._stochastic_update(date)

    def _stochastic_update(self, date: datetime):
        month  = date.month
        season = ("WINTER" if month in (12, 1, 2) else
                  "SPRING" if month in (3, 4, 5) else
                  "SUMMER" if month in (6, 7, 8) else "FALL")

        self.weather = random.choices(
            population=WEATHER_TYPES,
            weights=SEASON_PROBABILITY_FACTOR[season],
            k=1,
        )[0]
        lo, hi             = CLOUD_COVERAGE[self.weather]
        self.cloud_coverage = random.uniform(lo, hi)
        self.cloud_type     = int(self.cloud_coverage * 12)
        self.temperature    = 20.0
        self.humidity       = 50.0
        self.zenith         = 45.0
        self.ghi            = max(0.0, 600.0 * (1 - self.cloud_coverage))
        self.clearsky_ghi   = 700.0


def _coverage_label(coverage: float) -> str:
    if coverage < 0.15:
        return "CLEAR"
    if coverage < 0.45:
        return "PARTLY_CLOUDY"
    if coverage < 0.75:
        return "MOSTLY_CLOUDY"
    return "OVERCAST"
