"""
Configuration file for the Green Grid Digital Twin simulation.

All tunable parameters for the simulation are defined here.
Adjust these values to model different solar system setups,
battery sizes, weather patterns, and energy strategies.
"""

from enum import Enum

# ── Simulation Time ──────────────────────────────────────────────────────────
SIMULATION_DAYS = 30                # Number of days to simulate
MINUTES_PER_TICK = 15               # Minutes per simulation tick (60 = 1-hour resolution)
DATE_OF_SIMULATION = "01/6/2026"   # Simulation start date (dd/mm/yyyy)

# ── Battery ──────────────────────────────────────────────────────────────────
BATTERY_CAPACITY = 13.5             # Total battery capacity in Wh (e.g., 13.5 kWh)
BATTERY_FLOOR = 0.05                # Minimum usable state-of-charge (fraction, 0.0–1.0)
ROUND_TRIP_EFFICIENCY = 0.95        # Battery round-trip efficiency (fraction, 0.0–1.0)

# ── Inverter ─────────────────────────────────────────────────────────────────
INVERTER_CLIPPING = 4               # Max inverter output in kW (generation above this is clipped)
INVERTER_FAIL_PROB = 0.01           # Probability of inverter failure per tick (0.0–1.0)
MIN_INVERTER_FAIL_DURATION = 4
MAX_INVERTER_FAIL_DURATION = 72     # Duration of an inverter failure in ticks (hours)

# ── Grid ─────────────────────────────────────────────────────────────────────
GRID_CONSTRAINT = 20                # Max grid export limit in kW

# ── Solar Panel ──────────────────────────────────────────────────────────────
SOLAR_PEAK = 5                      # Peak solar panel output in kW (e.g., 5 kW)

# ── Household ────────────────────────────────────────────────────────────────
BASE_LOAD = 0.5                     # Base household load in kW (constant consumption)
MAX_PEAK_LOAD = 3                   # The load's maximum value when spiking during peak usage hours in kW
PEAK_USAGE_HOUR_START = 18          # The hour of the day when peak usage starts
PEAK_USAGE_HOUR_END = 21            # The hour of the day when peak usage ends

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
        }
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
        }
    },

    {
        "name": "Computer",
        "power_kW": 0.15,
        "usage": {
            **{h: 0.05 for h in range(0, 7)},
            **{h: 0.40 for h in range(7, 18)},
            **{h: 0.60 for h in range(18, 22)},
            **{h: 0.20 for h in range(22, 24)},
        }
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
        }
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
        }
    },

    {
        "name": "Electric Oven",
        "power_kW": 2.0,
        "usage": {
            **{h: 0.00 for h in range(0, 18)},
            **{h: 0.40 for h in range(18, 21)},
            **{h: 0.00 for h in range(21, 24)},
        }
    },
]

# ── Economics ────────────────────────────────────────────────────────────────
IMPORT_COST = 0.75                  # Cost per kWh imported from the grid (currency units)
EXPORT_COST = 0.90                  # Revenue per kWh exported to the grid (currency units)

# ── Energy Management Strategy ───────────────────────────────────────────────
class PRIORITY_OPTIONS(Enum):
    """Defines how surplus solar energy is allocated each tick."""
    LOAD = 1                        # Serve household load first, then battery, then export
    CHARGE = 2                      # Charge battery first, then serve load, then export
    PRODUCE = 3                     # Export to grid first, then battery, then serve load

CHARGE_PRIORITY = PRIORITY_OPTIONS.LOAD  # Active strategy used by the simulation


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
