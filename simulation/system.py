import csv
from datetime import datetime, timedelta
from simpy import Environment
from config import *

from components.battery import Battery
from components.panel import Panel
from components.weather import Weather
from components.inverter import Inverter
from components.grid import Grid
from components.home import Home

def Simulate(env, weather, panel, home, inverter, battery, grid, bitacora, stats):
    dt = datetime.strptime(DATE_OF_SIMULATION, "%d/%m/%Y")
    
    while True:
        if env.now % 24 == 0:
            weather.update(dt)

        panel.update(weather.cloud_coverage)
        home.update()
        inverter.update(panel.generation, home.totalLoad)
        battery.update()
        
        stats["soc_history"].append(battery.batteryPercentage)
        stats["cloud_history"].append(weather.cloud_coverage)
        stats["load_history"].append(home.totalLoad)
        
        if battery.batteryPercentage >= 99.9: stats["full_hours"] += 1
        if battery.batteryPercentage <= 0.1: stats["empty_hours"] += 1
        
        unmet = max(0, home.totalLoad - (panel.generation + battery.level)) if inverter.is_failed else 0
        if unmet > 0: stats["unmet_events"] += 1

       
        bitacora.append({
            "Timestamp": dt.strftime("%Y-%m-%d %H:%M"),
            "Solar_Wh": f"{panel.generation:.2f}",
            "House_Load_Wh": f"{home.totalLoad:.2f}",
            "SoC_%": f"{battery.batteryPercentage:.2f}",
            "Grid_Net_Wh": f"{inverter.last_grid_flow:.2f}",
            "Cloud_Cov": f"{weather.cloud_coverage:.2f}",
            "Inverter_OK": not inverter.is_failed
        })

        dt += timedelta(minutes=MINUTES_PER_TICK)
        yield env.timeout(MINUTES_PER_TICK / 60)

def main() -> None:
    print(f"\n--- GREEN GRID DIGITAL TWIN | INICIANDO SIMULACIÓN MENSUAL ---")
    env = Environment()
    

    battery = Battery(env, initial_charge=0, capacity=BATTERY_CAPACITY)
    weather = Weather(env)
    panel = Panel(env, battery, weather)
    home = Home(env)
    grid = Grid()
    inverter = Inverter(env, panel, battery, home, grid, CHARGE_PRIORITY)
    
  
    bitacora = []
    stats = {
        "soc_history": [], "cloud_history": [], "load_history": [],
        "full_hours": 0, "empty_hours": 0, "unmet_events": 0
    }
    

    env.process(Simulate(env, weather, panel, home, inverter, battery, grid, bitacora, stats))
    env.run(until=SIMULATION_DAYS * 24)

    
    avg_soc = sum(stats["soc_history"]) / len(stats["soc_history"])
    avg_cloud = sum(stats["cloud_history"]) / len(stats["cloud_history"])
    peak_load = max(stats["load_history"])
    

    total_import_kwh = inverter.metrics['total_grid_import'] / 1000
    total_export_kwh = inverter.metrics['total_grid_export'] / 1000
    gasto = total_import_kwh * IMPORT_COST
    ganancia = total_export_kwh * EXPORT_COST
    balance_neto = ganancia - gasto

 
    print("\n" + "="*55)
    print("        TECHNICAL REPORT - SIMULATION SUMMARY (30 DAYS)        ")
    print("="*55)
    print(f"1. Average Monthly SoC:           {avg_soc:.2f}%")
    print(f"2. Hours Battery Full:            {stats['full_hours']} hrs")
    print(f"3. Hours Battery Empty:           {stats['empty_hours']} hrs")
    print(f"4. Total Solar Energy:            {inverter.metrics['total_solar_gen']/1000:.2f} kWh")
    print(f"5. Total Household Consumption:   {inverter.metrics['total_load_served']/1000:.2f} kWh")
    print(f"6. Inverter Failures:             {inverter.fail_count} events")
    print(f"7. Total Downtime:                {inverter.total_downtime} hrs")
    print(f"8. Average Cloud Coverage:        {avg_cloud:.2f}")
    print(f"9. Peak Load Demand:              {peak_load:.2f} W")
    print(f"10. Unmet Load Events:            {stats['unmet_events']}")
    print("-" * 55)
    print(f">> ECONOMIC BALANCE: {balance_neto:.2f} cents")
    print(f"   (Cost: -{gasto:.2f} | Credit: +{ganancia:.2f})")
    print("="*55)

    with open('Monthly_Summary.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=bitacora[0].keys())
        writer.writeheader()
        writer.writerows(bitacora)
    
    print(f"\n>>> Simulation finished. Log with {len(bitacora)} records saved.")

if __name__ == '__main__':
    main()