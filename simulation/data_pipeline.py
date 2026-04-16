"""
Data preparation pipeline.

Reads the raw per-tick CSVs produced by ``simulation.py`` and writes
dashboard-ready datasets to ``dashboard/data/``. The pipeline is invoked
automatically at the end of a simulation run (see ``simulation.main``) so the
information flow to the dashboard is transparent — no manual file moving
required. It is also runnable standalone::

    python data_pipeline.py
"""

import json
import os
from datetime import datetime

import pandas as pd

from config import (
    IMPORT_COST,
    EXPORT_COST,
    MINUTES_PER_TICK,
    SCENARIO_NAME,
)

SIM_DIR = os.path.dirname(os.path.abspath(__file__))
SIM_OUTPUT_DIR = os.path.join(SIM_DIR, "output")
DASHBOARD_DATA_DIR = os.path.normpath(os.path.join(SIM_DIR, "..", "dashboard", "data"))

TIME_FACTOR = MINUTES_PER_TICK / 60


def _enrich_time(df: pd.DataFrame, ts_col: str = "timestamp") -> pd.DataFrame:
    """Add date/hour/week/month/quarter/year columns for fast filtering."""
    df = df.copy()
    df[ts_col] = pd.to_datetime(df[ts_col])
    df["date"] = df[ts_col].dt.date
    df["hour"] = df[ts_col].dt.hour
    df["day_of_week"] = df[ts_col].dt.day_name()
    df["is_weekend"] = df[ts_col].dt.dayofweek >= 5
    df["week"] = df[ts_col].dt.to_period("W-MON").astype(str)
    df["month"] = df[ts_col].dt.to_period("M").astype(str)
    df["quarter"] = df[ts_col].dt.to_period("Q").astype(str)
    df["year"] = df[ts_col].dt.year
    return df


def build(sim_output_dir: str = SIM_OUTPUT_DIR,
          dashboard_data_dir: str = DASHBOARD_DATA_DIR) -> dict:
    """Transform raw outputs into dashboard-ready CSVs. Returns a manifest."""
    os.makedirs(dashboard_data_dir, exist_ok=True)

    ticks = pd.read_csv(os.path.join(sim_output_dir, "HouseholdsSummary.csv"))
    system = pd.read_csv(os.path.join(sim_output_dir, "SystemSummary.csv"))
    meta = pd.read_csv(os.path.join(sim_output_dir, "HouseholdsMeta.csv"))

    ticks = _enrich_time(ticks)
    system = _enrich_time(system)

    # Signed net grid flow from the household's perspective:
    #  > 0  : exporting to grid
    #  < 0  : importing from grid
    ticks["net_kWh"] = ticks["grid_exports_kWh"] - ticks["grid_imports_kWh"]

    # ── Daily rollup per household ─────────────────────────────────────────
    daily = (ticks.groupby(
                ["date", "house_id", "type", "wealth", "strategy",
                 "has_solar", "has_battery"],
                as_index=False)
             .agg(generation_kWh=("generation_kWh", "sum"),
                  load_kWh=("load_kWh", "sum"),
                  self_consumption_kWh=("self_consumption_kWh", "sum"),
                  grid_imports_kWh=("grid_imports_kWh", "sum"),
                  grid_exports_kWh=("grid_exports_kWh", "sum"),
                  cost=("tick_cost", "sum"),
                  savings=("tick_savings", "sum"),
                  avg_soc=("soc", "mean"),
                  inverter_down_ticks=("inverter_ok", lambda x: int((~x).sum()))))
    daily["inverter_down_hours"] = daily["inverter_down_ticks"] * TIME_FACTOR
    daily = daily.drop(columns=["inverter_down_ticks"])

    # ── Hour-of-day × (type, wealth) — feeds the duck curve ────────────────
    duck = (ticks.groupby(["hour", "type", "wealth"], as_index=False)
                 .agg(mean_gen_kWh=("generation_kWh", "mean"),
                      mean_load_kWh=("load_kWh", "mean"),
                      mean_imports_kWh=("grid_imports_kWh", "mean"),
                      mean_exports_kWh=("grid_exports_kWh", "mean"),
                      mean_soc=("soc", "mean")))
    duck["mean_net_load_kWh"] = duck["mean_load_kWh"] - duck["mean_gen_kWh"]

    # ── Neighborhood-wide duck curve (flat) ────────────────────────────────
    duck_total = (ticks.groupby(["hour"], as_index=False)
                        .agg(mean_gen_kWh=("generation_kWh", "mean"),
                             mean_load_kWh=("load_kWh", "mean"),
                             mean_imports_kWh=("grid_imports_kWh", "mean"),
                             mean_exports_kWh=("grid_exports_kWh", "mean"),
                             mean_soc=("soc", "mean")))
    duck_total["mean_net_load_kWh"] = duck_total["mean_load_kWh"] - duck_total["mean_gen_kWh"]

    # ── Segment summary (type × wealth totals for the whole run) ───────────
    segment = (daily.groupby(["type", "wealth"], as_index=False)
                    .agg(houses=("house_id", "nunique"),
                         generation_kWh=("generation_kWh", "sum"),
                         load_kWh=("load_kWh", "sum"),
                         self_consumption_kWh=("self_consumption_kWh", "sum"),
                         imports_kWh=("grid_imports_kWh", "sum"),
                         exports_kWh=("grid_exports_kWh", "sum"),
                         cost=("cost", "sum"),
                         savings=("savings", "sum")))
    segment["net_balance"] = segment["exports_kWh"] * EXPORT_COST - segment["imports_kWh"] * IMPORT_COST
    segment["self_consumption_pct"] = (segment["self_consumption_kWh"] /
                                       segment["load_kWh"] * 100).fillna(0)

    # ── Adoption rates by segment ──────────────────────────────────────────
    adoption = (meta.groupby(["type", "wealth"], as_index=False)
                    .agg(houses=("house_id", "count"),
                         solar_homes=("has_solar", "sum"),
                         battery_homes=("has_battery", "sum")))
    adoption["solar_adoption_pct"] = adoption["solar_homes"] / adoption["houses"] * 100
    adoption["battery_adoption_pct"] = adoption["battery_homes"] / adoption["houses"] * 100

    # ── Write everything ───────────────────────────────────────────────────
    outputs = {
        "ticks.csv": ticks,
        "system.csv": system,
        "households.csv": meta,
        "daily_by_household.csv": daily,
        "hourly_by_segment.csv": duck,
        "hourly_neighborhood.csv": duck_total,
        "segment_summary.csv": segment,
        "adoption.csv": adoption,
    }
    for name, df in outputs.items():
        df.to_csv(os.path.join(dashboard_data_dir, name), index=False)

    manifest = {
        "scenario": SCENARIO_NAME,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tick_minutes": MINUTES_PER_TICK,
        "import_cost": IMPORT_COST,
        "export_cost": EXPORT_COST,
        "n_households": int(meta["house_id"].nunique()),
        "n_ticks": int(len(system)),
        "start": pd.to_datetime(system["timestamp"]).min().isoformat(),
        "end": pd.to_datetime(system["timestamp"]).max().isoformat(),
        "files": sorted(outputs.keys()),
    }
    with open(os.path.join(dashboard_data_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def main() -> None:
    m = build()
    print(f"Pipeline complete. Wrote dashboard-ready CSVs to {DASHBOARD_DATA_DIR}")
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
