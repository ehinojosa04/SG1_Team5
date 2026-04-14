import pandas as pd
import os
from datetime import datetime, timedelta
from simpy import Environment
from config import *

from components.weather import Weather
from components.houseUnit import HouseUnit

def runSimulation(env, weather, houses: list[HouseUnit], house_logs, system_logs):
    dt = datetime.strptime(DATE_OF_SIMULATION, "%d/%m/%Y")
    time_factor = MINUTES_PER_TICK / 60
    
    while True:
        if dt.hour == 0 and dt.minute == 0:
            weather.update(dt)

        total_load = 0
        total_generation = 0
        total_imports = 0
        total_exports = 0

        for house in houses:
            if dt.hour == 0 and dt.minute == 0:
                house.dailyUpdate(dt)
            
            data = house.stepUpdate(weather, dt, time_factor)

            total_generation += data['generation_kWh']
            total_load += data['load_kWh']
            total_imports += data['grid_imports_kWh']
            total_exports += data['grid_exports_kWh']

            house_logs.append({"timestamp": dt, **data})
        
        system_logs.append({"timestamp": dt, 
                            "total_load": total_load, 
                            "total_generation": total_generation, 
                            "net_load": total_load - total_generation,
                            "total_imports": total_imports,
                            "total_exports": total_exports,
                            "cloud_coverage": weather.cloud_coverage})

        dt += timedelta(minutes=MINUTES_PER_TICK)
        yield env.timeout(MINUTES_PER_TICK / 60)

def main() -> None:
    print(f"\n--- GREEN GRID DIGITAL TWIN | INICIANDO SIMULACIÓN MENSUAL ---")
    env = Environment()
    weather = Weather(env)
    houses: list[HouseUnit] = []

    house_id = 0

    for group in NEIGHBORHOOD_CONFIG:
        for _ in range(group["count"]):
            h_type = group["type"]
            wealth = group["wealth"]
            priority = group['charge_priority']

            houses.append(HouseUnit(env, weather, house_id, h_type, wealth, priority))

            house_id += 1

    house_logs = []
    system_logs = []
    
    env.process(runSimulation(env, weather, houses, house_logs, system_logs))
    env.run(until=SIMULATION_DAYS * 24)

    df_house = pd.DataFrame(house_logs)
    df_system = pd.DataFrame(system_logs)

    print("\n" + "="*70)
    print(f"TECHNICAL REPORT - SIMULATION SUMMARY ({DATE_OF_SIMULATION} - {(datetime.strptime(DATE_OF_SIMULATION, "%d/%m/%Y") + timedelta(days=SIMULATION_DAYS)).strftime("%d/%m/%Y")})")
    print("\n" + "="*70)
    for house in houses:
        individual_logs = df_house[df_house.house_id == house.id]

        value = individual_logs.load_kWh.max()
        print(value)
        print(type(value))

        print("="*70)
        print(f"1.  Energy Management Strategy:         {house.charge_priority.name}")
        print(f"2.  Average Monthly SoC:                {individual_logs.soc.mean():.2f}%")
        print(f"3.  Hours Battery Full:                 {len(individual_logs[individual_logs.soc > 99])} hrs")
        print(f"4.  Hours Battery Empty:                {len(individual_logs[individual_logs.soc < 0.1])} hrs")
        print(f"5.  Total Solar Energy:                 {individual_logs.generation_kWh.sum():.2f} kWh")
        print(f"6.  Avg. Daily Solar Energy:            {individual_logs.groupby(pd.to_datetime(individual_logs['timestamp']).dt.date)['generation_kWh'].sum().mean():.2f} kWh")
        print(f"7.  Total Household Consumption:        {individual_logs.load_kWh.sum():.2f} kWh")
        print(f"8.  Avg. Daily Household Consumption:   {individual_logs.groupby(pd.to_datetime(individual_logs['timestamp']).dt.date)['load_kWh'].sum().mean():.2f} kWh")
        print(f"9.  Grid imports / exports              {individual_logs.grid_imports_kWh.sum():.2f} / {individual_logs.grid_exports_kWh.sum():.2f}")
        print(f"10. Inverter Failures:                  {house.inverter.fail_count} events")
        print(f"11. Total Downtime:                     {(MINUTES_PER_TICK / 60) * len(individual_logs[individual_logs.inverter_ok == False])} hrs")
        print(f"12. Average Cloud Coverage:             {df_system.cloud_coverage.mean():.2f}")
        print(f"13. Peak Load Demand:                   {individual_logs.load_kWh.max().item():.2f} W")
        # PREGUNTAR SI LOS GRID IMPORTS CUENTAN EN LOS UNMET LOADS AKA SI UNMET LOAD EVENTS == INVERTER FAILURES
        print(f"14. Unmet Load Events:                  {len((individual_logs[((individual_logs.soc < 0.1) & (individual_logs.generation_kWh < 0.1) | (individual_logs.inverter_ok == False))]))}")
        print("-" * 55)
        balance = df_system.net_load.sum()
        print(f">> ECONOMIC BALANCE: {'-' if balance < 0 else ''} $ {abs(balance):.2f}")
        print(f"   (Cost: -{df_system.total_imports.sum():.2f} | Credit: +{df_system.total_exports.sum():.2f})")
        print("="*70)
    
    os.makedirs(os.path.dirname("./simulation/output/"), exist_ok=True)
    df_house.to_csv("./simulation/output/HouseholdsSummary.csv")
    df_system.to_csv("./simulation/output/SystemSummary.csv")

    print(f"\n>>> Simulation finished. Log with {len(df_house)} records saved.")
    

if __name__ == '__main__':
    main()
