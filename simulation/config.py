"""
Configuration file for the Green Grid Digital Twin simulation.

All tunable parameters for the simulation are defined here.
Adjust these values to model different solar system setups,
battery sizes, weather patterns, and energy strategies.
"""

from enum import Enum

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

# ── Simulation Time ──────────────────────────────────────────────────────────
SIMULATION_DAYS = 30                # Number of days to simulate
MINUTES_PER_TICK = 30               # Minutes per simulation tick (60 = 1-hour resolution)
DATE_OF_SIMULATION = "01/1/2026"   # Simulation start date (dd/mm/yyyy)

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
