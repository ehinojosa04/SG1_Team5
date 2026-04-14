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
    time_factor = MINUTES_PER_TICK / 60
    
    while True:
        if dt.hour == 0 and dt.minute == 0:
            weather.update(dt)
            inverter.updateCondition()
            grid.update(dt.day)

        panel.update(dt.hour, weather.cloud_coverage)
        home.update(dt.hour)

        generation_kWh = panel.generation * time_factor
        load_kWh = home.totalLoad * time_factor

        inverter.update(generation_kWh, load_kWh, time_factor)
        battery.update()
        
        stats["soc_history"].append(battery.batteryPercentage)
        stats["cloud_history"].append(weather.cloud_coverage)
        stats["load_history"].append(home.totalLoad)
        
        if battery.batteryPercentage >= 99.9: stats["full_hours"] += time_factor
        if battery.batteryPercentage <= 0.1: stats["empty_hours"] += time_factor
        
        unmet = max(0, load_kWh - (generation_kWh + battery.level)) if inverter.is_failed else 0
        if unmet > 0: stats["unmet_events"] += 1

        print(f"{dt}: SoC: {battery.batteryPercentage:.2f}%, gen: {generation_kWh:.2f}, load: {load_kWh:.2f} ({", ".join([a.name for a in home.appliances if a.is_on])})")

       
        bitacora.append({
            "Timestamp": dt.strftime("%Y-%m-%d %H:%M"),
            "Solar_kWh": f"{generation_kWh:.2f}",
            "House_Load_kWh": f"{load_kWh:.2f}",
            "SoC_%": f"{battery.batteryPercentage:.2f}",
            "Grid_Net_kWh": f"{inverter.last_grid_flow:.2f}",
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
    grid = Grid(env)
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
    
    
    gasto = inverter.metrics['total_grid_import'] * IMPORT_COST
    ganancia = inverter.metrics['total_grid_export'] * EXPORT_COST
    balance_neto = ganancia - gasto

 
    print("\n" + "="*70)
    print(f"TECHNICAL REPORT - SIMULATION SUMMARY ({DATE_OF_SIMULATION} - {(datetime.strptime(DATE_OF_SIMULATION, "%d/%m/%Y") + timedelta(days=SIMULATION_DAYS)).strftime("%d/%m/%Y")})")
    print("="*70)
    print(f"1.  Energy Management Strategy:    {CHARGE_PRIORITY.name}")
    print(f"2.  Average Monthly SoC:           {avg_soc:.2f}%")
    print(f"3.  Hours Battery Full:            {stats['full_hours']} hrs")
    print(f"4.  Hours Battery Empty:           {stats['empty_hours']} hrs")
    print(f"5.  Total Solar Energy:            {inverter.metrics['total_solar_gen']:.2f} kWh")
    print(f"6.  Avg. Solar Energy:             {inverter.metrics['total_solar_gen']/SIMULATION_DAYS:.2f} kWh")
    print(f"7.  Total Household Consumption:   {inverter.metrics['total_load_served']:.2f} kWh")
    print(f"8.  Avg. Household Consumption:    {inverter.metrics['total_load_served']/SIMULATION_DAYS:.2f} kWh")
    print(f"9.  Grid imports / exports         {inverter.metrics['total_grid_import']:.2f} / {inverter.metrics['total_grid_export']:.2f}")
    print(f"10. Inverter Failures:             {inverter.fail_count} events")
    print(f"11. Total Downtime:                {inverter.total_downtime} hrs")
    print(f"12. Average Cloud Coverage:        {avg_cloud:.2f}")
    print(f"13. Peak Load Demand:              {peak_load:.2f} W")
    print(f"14. Unmet Load Events:             {stats['unmet_events']}")
    print("-" * 55)
    print(f">> ECONOMIC BALANCE: {'-' if balance_neto < 0 else ''} $ {abs(balance_neto):.2f}")
    print(f"   (Cost: -{gasto:.2f} | Credit: +{ganancia:.2f})")
    print("="*70)

    with open('simulation/Monthly_Summary.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=bitacora[0].keys())
        writer.writeheader()
        writer.writerows(bitacora)
    
    print(f"\n>>> Simulation finished. Log with {len(bitacora)} records saved.")

if __name__ == '__main__':
    main()
