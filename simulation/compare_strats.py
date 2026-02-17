import simpy
from config import *

from components.battery import Battery
from components.panel import Panel
from components.weather import Weather
from components.inverter import Inverter
from components.grid import Grid
from components.home import Home
from system import Simulate 

def run_scenario(strategy_name, priority_enum):
    """
    Runs a complete simulation for a specific energy management strategy.
    Returns a dictionary with key performance metrics.
    """
    print(f"Running simulation for: {strategy_name}...")
    
    env = simpy.Environment()
   
    battery = Battery(env, initial_charge=0, capacity=BATTERY_CAPACITY)
    weather = Weather(env)
    panel = Panel(env, battery, weather)
    home = Home(env)
    grid = Grid()
    
    inverter = Inverter(env, panel, battery, home, grid, priority_enum)
    
    dummy_log = [] 
    stats = {
        "soc_history": [], "cloud_history": [], "load_history": [],
        "full_hours": 0, "empty_hours": 0, "unmet_events": 0
    }
    
    env.process(Simulate(env, weather, panel, home, inverter, battery, grid, dummy_log, stats))
    env.run(until=SIMULATION_DAYS * 24)
    
    total_import_kwh = inverter.metrics['total_grid_import'] / 1000
    total_export_kwh = inverter.metrics['total_grid_export'] / 1000
    
    cost = total_import_kwh * IMPORT_COST
    revenue = total_export_kwh * EXPORT_COST
    net_balance = revenue - cost
    
    return {
        "Strategy": strategy_name,
        "Net_Balance": net_balance,
        "Import_kWh": total_import_kwh,
        "Export_kWh": total_export_kwh,
        "Unmet_Events": stats['unmet_events'],
        "Inverter_Failures": inverter.fail_count
    }

def main():
    print("\n" + "="*80)
    print("   GREEN GRID - STRATEGY COST-EFFECTIVENESS ANALYSIS (SG1_TEAM5)")
    print("="*80 + "\n")
    
    results = []
    
    results.append(run_scenario("LOAD PRIORITY", PRIORITY_OPTIONS.LOAD))
    
    results.append(run_scenario("CHARGE PRIORITY", PRIORITY_OPTIONS.CHARGE))
    
    results.append(run_scenario("PRODUCE PRIORITY", PRIORITY_OPTIONS.PRODUCE))
    
    print("\n" + "-"*100)
    print(f"{'STRATEGY':<20} | {'BALANCE (cents)':<18} | {'IMPORT (kWh)':<15} | {'EXPORT (kWh)':<15} | {'UNMET LOAD'}")
    print("-"*100)
    
    best_strategy = ""
    best_balance = -float('inf')
    
    for r in results:
        balance_str = f"{r['Net_Balance']:.2f}"
        print(f"{r['Strategy']:<20} | {balance_str:<18} | {r['Import_kWh']:<15.2f} | {r['Export_kWh']:<15.2f} | {r['Unmet_Events']}")
        
        if r['Net_Balance'] > best_balance:
            best_balance = r['Net_Balance']
            best_strategy = r['Strategy']
            
    print("-"*100)
    print(f"\n>>> CONCLUSION: The most cost-effective strategy is {best_strategy}")
    print(f"    with a Net Balance of {best_balance:.2f} cents.")
    print("="*100)

if __name__ == '__main__':
    main()