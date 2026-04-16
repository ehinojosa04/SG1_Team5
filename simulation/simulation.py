import os
import random
from datetime import datetime, timedelta

import pandas as pd
from simpy import Environment

from config import (
    DATE_OF_SIMULATION,
    SIMULATION_DAYS,
    MINUTES_PER_TICK,
    NEIGHBORHOOD_CONFIG,
    SCENARIO_NAME,
    IMPORT_COST,
    EXPORT_COST,
    RANDOM_SEED,
)
from components.weather import Weather
from components.houseUnit import HouseUnit


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def runSimulation(env, weather, houses, house_logs, system_logs):
    dt = datetime.strptime(DATE_OF_SIMULATION, "%d/%m/%Y")
    time_factor = MINUTES_PER_TICK / 60

    while True:
        # New day: refresh weather and each house's daily-scale state
        if dt.hour == 0 and dt.minute == 0:
            weather.update(dt)
            for house in houses:
                house.dailyUpdate(dt)

        total_load = 0.0
        total_generation = 0.0
        total_imports = 0.0
        total_exports = 0.0
        total_self_consumption = 0.0
        total_savings = 0.0

        for house in houses:
            data = house.stepUpdate(weather, dt, time_factor)

            total_generation += data["generation_kWh"]
            total_load += data["load_kWh"]
            total_imports += data["grid_imports_kWh"]
            total_exports += data["grid_exports_kWh"]
            total_self_consumption += data["self_consumption_kWh"]
            total_savings += data["tick_savings"]

            house_logs.append({"timestamp": dt, **data})

        system_logs.append({
            "timestamp": dt,
            "total_load_kWh": total_load,
            "total_generation_kWh": total_generation,
            "total_self_consumption_kWh": total_self_consumption,
            "net_load_kWh": total_load - total_generation,
            "total_imports_kWh": total_imports,
            "total_exports_kWh": total_exports,
            "tick_savings": total_savings,
            "cloud_coverage": weather.cloud_coverage,
        })

        dt += timedelta(minutes=MINUTES_PER_TICK)
        yield env.timeout(time_factor)


def build_houses(env, weather):
    houses = []
    house_id = 0
    for group in NEIGHBORHOOD_CONFIG:
        for _ in range(group["count"]):
            houses.append(HouseUnit(
                env, weather, house_id,
                group["type"], group["wealth"], group["charge_priority"],
            ))
            house_id += 1
    return houses


def print_neighborhood_report(houses, df_house, df_system, start_dt, end_dt):
    n_houses = len(houses)
    n_solar = sum(1 for h in houses if h.has_solar)
    n_batt = sum(1 for h in houses if h.has_battery)

    total_gen = df_house.generation_kWh.sum()
    total_load = df_house.load_kWh.sum()
    total_self = df_house.self_consumption_kWh.sum()
    total_imp = df_house.grid_imports_kWh.sum()
    total_exp = df_house.grid_exports_kWh.sum()
    total_cost = total_imp * IMPORT_COST
    total_credit = total_exp * EXPORT_COST
    total_balance = total_credit - total_cost
    total_savings = df_house.tick_savings.sum()

    print("\n" + "=" * 72)
    print(f"  NEIGHBORHOOD REPORT  |  scenario: {SCENARIO_NAME}")
    print(f"  {start_dt.strftime('%d/%m/%Y')}  →  {end_dt.strftime('%d/%m/%Y')}")
    print("=" * 72)
    print(f"Households simulated:        {n_houses}")
    print(f"  with solar panels:         {n_solar}  ({n_solar/n_houses:.0%})")
    print(f"  with home batteries:       {n_batt}  ({n_batt/n_houses:.0%})")
    print(f"Total generation:            {total_gen:,.1f} kWh")
    print(f"Total consumption:           {total_load:,.1f} kWh")
    print(f"Total self-consumption:      {total_self:,.1f} kWh  ({(total_self/total_load*100 if total_load else 0):.1f}% of load)")
    print(f"Grid imports:                {total_imp:,.1f} kWh")
    print(f"Grid exports:                {total_exp:,.1f} kWh")
    print(f"Average cloud coverage:      {df_system.cloud_coverage.mean():.2f}")
    print("-" * 72)
    print(f"Neighborhood import cost:    $ {total_cost:,.2f}")
    print(f"Neighborhood export credit:  $ {total_credit:,.2f}")
    print(f"Net balance:                 $ {total_balance:,.2f}")
    print(f"Savings vs. no-solar baseline: $ {total_savings:,.2f}")
    print("=" * 72)

    # Per-segment summary: type × wealth
    seg = (df_house.groupby(["type", "wealth"])
                   .agg(houses=("house_id", "nunique"),
                        gen=("generation_kWh", "sum"),
                        load=("load_kWh", "sum"),
                        imp=("grid_imports_kWh", "sum"),
                        exp=("grid_exports_kWh", "sum"))
                   .reset_index())
    seg["net_$"] = seg["exp"] * EXPORT_COST - seg["imp"] * IMPORT_COST
    print("\nSegment breakdown (type × wealth):")
    print(seg.to_string(index=False, formatters={
        "gen": "{:,.1f}".format, "load": "{:,.1f}".format,
        "imp": "{:,.1f}".format, "exp": "{:,.1f}".format,
        "net_$": "{:,.2f}".format,
    }))


def main() -> None:
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    print(f"\n--- GREEN GRID DIGITAL TWIN | scenario={SCENARIO_NAME} ---")
    env = Environment()
    weather = Weather(env)
    houses = build_houses(env, weather)

    house_logs: list[dict] = []
    system_logs: list[dict] = []

    env.process(runSimulation(env, weather, houses, house_logs, system_logs))
    env.run(until=SIMULATION_DAYS * 24)

    df_house = pd.DataFrame(house_logs)
    df_system = pd.DataFrame(system_logs)

    # Household metadata table — static attributes of each household.
    df_houses_meta = pd.DataFrame([{
        "house_id": h.id,
        "type": h.type,
        "wealth": h.wealth,
        "strategy": h.charge_priority.name,
        "has_solar": h.has_solar,
        "has_battery": h.has_battery,
        "pv_kwp": h.pv_kwp,
        "batt_kwh": h.batt_kwh,
    } for h in houses])

    start_dt = datetime.strptime(DATE_OF_SIMULATION, "%d/%m/%Y")
    end_dt = start_dt + timedelta(days=SIMULATION_DAYS)

    print_neighborhood_report(houses, df_house, df_system, start_dt, end_dt)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_house.to_csv(os.path.join(OUTPUT_DIR, "HouseholdsSummary.csv"), index=False)
    df_system.to_csv(os.path.join(OUTPUT_DIR, "SystemSummary.csv"), index=False)
    df_houses_meta.to_csv(os.path.join(OUTPUT_DIR, "HouseholdsMeta.csv"), index=False)

    print(f"\n>>> Simulation finished. {len(df_house):,} household-ticks and "
          f"{len(df_system):,} system-ticks written to {OUTPUT_DIR}/")

    # Transparent hand-off to the dashboard: transform + publish the latest
    # outputs into dashboard/data/ without requiring any manual file moves.
    try:
        from data_pipeline import build as build_pipeline, DASHBOARD_DATA_DIR
        build_pipeline()
        print(f">>> Dashboard data refreshed in {DASHBOARD_DATA_DIR}/")
    except Exception as exc:
        print(f"[warn] Data pipeline failed: {exc}")


if __name__ == "__main__":
    main()
