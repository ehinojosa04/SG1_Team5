"""
Configuration file for the Green Grid Digital Twin simulation.

All tunable parameters for the simulation are defined here.
Adjust these values to model different solar system setups,
battery sizes, weather patterns, and energy strategies.

Scenarios
---------
Set the environment variable GG_SCENARIO to one of the keys in SCENARIOS
(e.g. "baseline", "high_adoption", "low_adoption") to override the default
neighborhood composition and adoption rates at runtime. Example:

    GG_SCENARIO=high_adoption python simulation.py
"""

import os
from enum import Enum

# ── Reproducibility ──────────────────────────────────────────────────────────
RANDOM_SEED = 42                    # Seed for random/adoption/weather (set to None for nondeterministic)

# ── Simulation Time ──────────────────────────────────────────────────────────
SIMULATION_DAYS = 30                # Number of days to simulate
MINUTES_PER_TICK = 15               # Minutes per simulation tick (60 = 1-hour resolution)
DATE_OF_SIMULATION = "01/6/2026"    # Simulation start date (dd/mm/yyyy)

# ── Battery ──────────────────────────────────────────────────────────────────
BATTERY_CAPACITY = 13.5             # Default battery capacity in kWh (used when a house has a battery)
BATTERY_FLOOR = 0.05                # Minimum usable state-of-charge (fraction, 0.0–1.0)
ROUND_TRIP_EFFICIENCY = 0.95        # Battery round-trip efficiency (fraction, 0.0–1.0)

# ── Inverter ─────────────────────────────────────────────────────────────────
INVERTER_CLIPPING = 4               # Max inverter output in kW (generation above this is clipped)
INVERTER_FAIL_PROB = 0.01           # Probability of inverter failure per tick (0.0–1.0)
MIN_INVERTER_FAIL_DURATION = 4
MAX_INVERTER_FAIL_DURATION = 72     # Max duration of an inverter failure (hours)

# ── Grid ─────────────────────────────────────────────────────────────────────
GRID_CONSTRAINT = 20                # Per-household max grid export limit in kW

# ── Solar Panel ──────────────────────────────────────────────────────────────
SOLAR_PEAK = 5                      # Default peak solar panel output in kW (used when a house has solar)

# ── Weather ──────────────────────────────────────────────────────────────────
# Probability weights for each weather type per season.
# Order must match WEATHER_TYPES: [CLEAR, PARTLY_CLOUDY, MOSTLY_CLOUDY, OVERCAST]
SEASON_PROBABILITY_FACTOR = {
    "SPRING": [0.3, 0.4, 0.2, 0.1],
    "SUMMER": [0.6, 0.3, 0.1, 0.0],
    "FALL":   [0.3, 0.3, 0.3, 0.1],
    "WINTER": [0.1, 0.2, 0.3, 0.4],
}

# Weather type labels used for sampling.
WEATHER_TYPES = ["CLEAR", "PARTLY_CLOUDY", "MOSTLY_CLOUDY", "OVERCAST"]

# Cloud coverage range (min, max) for each weather type (0.0 = clear sky, 1.0 = fully overcast).
CLOUD_COVERAGE = {
    "CLEAR":          (0.0, 0.2),
    "PARTLY_CLOUDY":  (0.2, 0.6),
    "MOSTLY_CLOUDY":  (0.6, 0.8),
    "OVERCAST":       (0.8, 0.9),
}

# ── Economics ────────────────────────────────────────────────────────────────
IMPORT_COST = 0.75                  # Cost per kWh imported from the grid (currency units)
EXPORT_COST = 0.90                  # Revenue per kWh exported to the grid (currency units)

# ── Energy Management Strategy ───────────────────────────────────────────────
class PRIORITY_OPTIONS(Enum):
    """Defines how surplus solar energy is allocated each tick."""
    LOAD = 1                        # Serve household load first, then battery, then export
    CHARGE = 2                      # Charge battery first, then serve load, then export
    PRODUCE = 3                     # Export to grid first, then battery, then serve load

# ── Household archetypes ─────────────────────────────────────────────────────
# base_load: minimum constant consumption (kW)
# peak_load: maximum simultaneous appliance+base load (kW)
HOUSEHOLD_LOADS = {
    "STUDIO": {"base_load": 0.2, "peak_load": 2.5},
    "SMALL":  {"base_load": 0.4, "peak_load": 4.5},
    "LARGE":  {"base_load": 0.8, "peak_load": 7.0},
}

# Per-appliance power is multiplied by the wealth multiplier as a proxy for
# bigger/more-modern appliances in wealthier homes.
WEALTH_MULTIPLIERS = {
    "LOW":    0.8,
    "MIDDLE": 1.0,
    "HIGH":   1.2,
    "LUXURY": 1.5,
}

# ── Solar / battery adoption (probabilistic, per wealth level) ───────────────
# Probability that a household of a given wealth level has solar panels installed.
SOLAR_ADOPTION_BY_WEALTH = {
    "LOW":    0.10,
    "MIDDLE": 0.35,
    "HIGH":   0.60,
    "LUXURY": 0.85,
}

# Probability that a household has a home battery. Realistically only makes
# sense when the house already has solar; we enforce that constraint at init.
BATTERY_ADOPTION_BY_WEALTH = {
    "LOW":    0.02,
    "MIDDLE": 0.15,
    "HIGH":   0.45,
    "LUXURY": 0.80,
}

# PV array size (kW peak) by wealth level, used when the house has solar.
SOLAR_SIZE_BY_WEALTH = {
    "LOW":    3.0,
    "MIDDLE": 5.0,
    "HIGH":   7.0,
    "LUXURY": 10.0,
}

# Battery size (kWh) by wealth level, used when the house has a battery.
BATTERY_SIZE_BY_WEALTH = {
    "LOW":    7.0,
    "MIDDLE": 13.5,
    "HIGH":   20.0,
    "LUXURY": 27.0,
}

# ── Neighborhood composition ─────────────────────────────────────────────────
# A realistic ~100-household neighborhood mixing all types × wealth levels.
# Charge priority can be varied to show strategy impact per segment.
BASELINE_NEIGHBORHOOD = [
    # STUDIO apartments: small, skew lower-income
    {"type": "STUDIO", "wealth": "LOW",    "charge_priority": PRIORITY_OPTIONS.LOAD,    "count": 12},
    {"type": "STUDIO", "wealth": "MIDDLE", "charge_priority": PRIORITY_OPTIONS.LOAD,    "count": 10},
    {"type": "STUDIO", "wealth": "HIGH",   "charge_priority": PRIORITY_OPTIONS.LOAD,    "count": 4},
    {"type": "STUDIO", "wealth": "LUXURY", "charge_priority": PRIORITY_OPTIONS.LOAD,    "count": 1},
    # SMALL single-family homes
    {"type": "SMALL",  "wealth": "LOW",    "charge_priority": PRIORITY_OPTIONS.LOAD,    "count": 8},
    {"type": "SMALL",  "wealth": "MIDDLE", "charge_priority": PRIORITY_OPTIONS.LOAD,    "count": 20},
    {"type": "SMALL",  "wealth": "HIGH",   "charge_priority": PRIORITY_OPTIONS.CHARGE,  "count": 12},
    {"type": "SMALL",  "wealth": "LUXURY", "charge_priority": PRIORITY_OPTIONS.CHARGE,  "count": 3},
    # LARGE family homes
    {"type": "LARGE",  "wealth": "LOW",    "charge_priority": PRIORITY_OPTIONS.LOAD,    "count": 3},
    {"type": "LARGE",  "wealth": "MIDDLE", "charge_priority": PRIORITY_OPTIONS.LOAD,    "count": 10},
    {"type": "LARGE",  "wealth": "HIGH",   "charge_priority": PRIORITY_OPTIONS.CHARGE,  "count": 12},
    {"type": "LARGE",  "wealth": "LUXURY", "charge_priority": PRIORITY_OPTIONS.PRODUCE, "count": 5},
]  # Total: 100 households

# Named scenarios — selected at runtime via env var GG_SCENARIO.
# Each scenario may override neighborhood composition and/or adoption rates.
SCENARIOS = {
    "baseline": {
        "neighborhood": BASELINE_NEIGHBORHOOD,
        "solar_adoption": SOLAR_ADOPTION_BY_WEALTH,
        "battery_adoption": BATTERY_ADOPTION_BY_WEALTH,
    },
    "high_adoption": {
        "neighborhood": BASELINE_NEIGHBORHOOD,
        "solar_adoption": {"LOW": 0.40, "MIDDLE": 0.70, "HIGH": 0.90, "LUXURY": 0.98},
        "battery_adoption": {"LOW": 0.15, "MIDDLE": 0.45, "HIGH": 0.75, "LUXURY": 0.95},
    },
    "low_adoption": {
        "neighborhood": BASELINE_NEIGHBORHOOD,
        "solar_adoption": {"LOW": 0.02, "MIDDLE": 0.10, "HIGH": 0.25, "LUXURY": 0.50},
        "battery_adoption": {"LOW": 0.00, "MIDDLE": 0.02, "HIGH": 0.10, "LUXURY": 0.30},
    },
}

_ACTIVE = SCENARIOS[os.environ.get("GG_SCENARIO", "baseline")]
SCENARIO_NAME = os.environ.get("GG_SCENARIO", "baseline")
NEIGHBORHOOD_CONFIG = _ACTIVE["neighborhood"]
SOLAR_ADOPTION_BY_WEALTH = _ACTIVE["solar_adoption"]
BATTERY_ADOPTION_BY_WEALTH = _ACTIVE["battery_adoption"]

# ── Appliances ───────────────────────────────────────────────────────────────
# Each appliance has a rated power (kW) and hourly usage probabilities.
APPLIANCES = [
    {
        "name": "Lighting",
        "power_kW": 0.3,
        "usage": {
            **{h: 0.01 for h in range(0, 6)},
            **{h: 0.40 for h in range(6, 8)},
            **{h: 0.10 for h in range(8, 18)},
            **{h: 0.85 for h in range(18, 22)},
            **{h: 0.20 for h in range(22, 24)},
        },
    },
    {
        "name": "TV",
        "power_kW": 0.2,
        "usage": {
            **{h: 0.05 for h in range(0, 6)},
            **{h: 0.15 for h in range(6, 9)},
            **{h: 0.10 for h in range(9, 17)},
            **{h: 0.70 for h in range(17, 22)},
            **{h: 0.30 for h in range(22, 24)},
        },
    },
    {
        "name": "Computer",
        "power_kW": 0.15,
        "usage": {
            **{h: 0.05 for h in range(0, 7)},
            **{h: 0.40 for h in range(7, 18)},
            **{h: 0.60 for h in range(18, 22)},
            **{h: 0.20 for h in range(22, 24)},
        },
    },
    {
        "name": "Microwave",
        "power_kW": 1.2,
        "usage": {
            **{h: 0.01 for h in range(0, 6)},
            **{h: 0.30 for h in range(6, 9)},
            **{h: 0.30 for h in range(13, 16)},
            **{h: 0.50 for h in range(18, 21)},
            **{h: 0.05 for h in range(21, 24)},
        },
    },
    {
        "name": "Dishwasher",
        "power_kW": 1.0,
        "usage": {
            **{h: 0.00 for h in range(0, 14)},
            **{h: 0.10 for h in range(14, 16)},
            **{h: 0.00 for h in range(16, 20)},
            **{h: 0.60 for h in range(20, 23)},
            **{h: 0.00 for h in range(23, 24)},
        },
    },
    {
        "name": "Electric Oven",
        "power_kW": 2.0,
        "usage": {
            **{h: 0.00 for h in range(0, 18)},
            **{h: 0.40 for h in range(18, 21)},
            **{h: 0.00 for h in range(21, 24)},
        },
    },
]
