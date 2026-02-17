import argparse
import contextlib
import io
import json
import random
import sys
from pathlib import Path
from statistics import mean

# Make local imports work no matter where the script is executed from.
SIM_DIR = Path(__file__).resolve().parent
if str(SIM_DIR) not in sys.path:
    sys.path.insert(0, str(SIM_DIR))

import simpy
import system
import config
from components.battery import Battery
from components.panel import Panel
from components.weather import Weather
from components.inverter import Inverter
from components.grid import Grid
from components.home import Home


def run_scenario(priority, start_date, seed=42, days=None):
    if days is None:
        days = config.SIMULATION_DAYS

    random.seed(seed)

    env = simpy.Environment()
    battery = Battery(env, initial_charge=0, capacity=config.BATTERY_CAPACITY)
    weather = Weather(env)
    panel = Panel(env, battery, weather)
    home = Home(env)
    grid = Grid()
    inverter = Inverter(env, panel, battery, home, grid, priority)

    bitacora = []
    stats = {
        'soc_history': [], 'cloud_history': [], 'load_history': [],
        'full_hours': 0, 'empty_hours': 0, 'unmet_events': 0,
    }

    old_date = system.DATE_OF_SIMULATION
    try:
        system.DATE_OF_SIMULATION = start_date
        with contextlib.redirect_stdout(io.StringIO()):
            env.process(system.Simulate(env, weather, panel, home, inverter, battery, grid, bitacora, stats))
            env.run(until=days * 24)
    finally:
        system.DATE_OF_SIMULATION = old_date

    imp_kwh = inverter.metrics['total_grid_import'] / 1000
    exp_kwh = inverter.metrics['total_grid_export'] / 1000
    solar_kwh = inverter.metrics['total_solar_gen'] / 1000
    load_kwh = inverter.metrics['total_load_served'] / 1000

    return {
        'avg_soc': mean(stats['soc_history']) if stats['soc_history'] else 0.0,
        'full_hours': stats['full_hours'],
        'empty_hours': stats['empty_hours'],
        'solar_kwh': solar_kwh,
        'load_kwh': load_kwh,
        'grid_import_kwh': imp_kwh,
        'grid_export_kwh': exp_kwh,
        'inverter_failures': inverter.fail_count,
        'total_downtime_h': inverter.total_downtime,
        'avg_cloud': mean(stats['cloud_history']) if stats['cloud_history'] else 0.0,
        'peak_load_w': max(stats['load_history']) if stats['load_history'] else 0.0,
        'unmet_events': stats['unmet_events'],
        'net_balance': exp_kwh * config.EXPORT_COST - imp_kwh * config.IMPORT_COST,
        'avg_failure_duration_h': (inverter.total_downtime / inverter.fail_count) if inverter.fail_count else 0.0,
        'log': bitacora,
    }


def build_results(seed=42):
    base = run_scenario(config.CHARGE_PRIORITY, config.DATE_OF_SIMULATION, seed=seed)

    strategies = {
        'LOAD_PRIORITY': run_scenario(config.PRIORITY_OPTIONS.LOAD, config.DATE_OF_SIMULATION, seed=seed),
        'CHARGE_PRIORITY': run_scenario(config.PRIORITY_OPTIONS.CHARGE, config.DATE_OF_SIMULATION, seed=seed),
        'PRODUCE_PRIORITY': run_scenario(config.PRIORITY_OPTIONS.PRODUCE, config.DATE_OF_SIMULATION, seed=seed),
    }

    cloud_bins = {
        'CLEAR(0.0-0.2)': [],
        'PARTLY_CLOUDY(0.2-0.6)': [],
        'MOSTLY_CLOUDY(0.6-0.8)': [],
        'OVERCAST(0.8-1.0)': [],
    }
    for r in base['log']:
        cloud = float(r['Cloud_Cov'])
        solar = float(r['Solar_Wh'])
        grid_net = float(r['Grid_Net_Wh'])
        soc = float(r['SoC_%'])
        row = {'solar_wh': solar, 'grid_import_wh': max(0.0, -grid_net), 'grid_export_wh': max(0.0, grid_net), 'soc': soc}
        if cloud < 0.2:
            cloud_bins['CLEAR(0.0-0.2)'].append(row)
        elif cloud < 0.6:
            cloud_bins['PARTLY_CLOUDY(0.2-0.6)'].append(row)
        elif cloud < 0.8:
            cloud_bins['MOSTLY_CLOUDY(0.6-0.8)'].append(row)
        else:
            cloud_bins['OVERCAST(0.8-1.0)'].append(row)

    cloud_summary = {}
    for k, rows in cloud_bins.items():
        if not rows:
            cloud_summary[k] = {'hours': 0}
            continue
        cloud_summary[k] = {
            'hours': len(rows),
            'avg_solar_wh_per_h': mean(x['solar_wh'] for x in rows),
            'avg_grid_import_wh_per_h': mean(x['grid_import_wh'] for x in rows),
            'avg_grid_export_wh_per_h': mean(x['grid_export_wh'] for x in rows),
            'avg_soc_percent': mean(x['soc'] for x in rows),
        }

    seasonal_dates = {
        'WINTER': '15/01/2026',
        'SPRING': '15/04/2026',
        'SUMMER': '15/07/2026',
        'FALL': '15/10/2026',
    }
    seasonal = {s: run_scenario(config.CHARGE_PRIORITY, d, seed=seed) for s, d in seasonal_dates.items()}

    return {
        'config': {
            'round_trip_efficiency': config.ROUND_TRIP_EFFICIENCY,
            'import_cost': config.IMPORT_COST,
            'export_cost': config.EXPORT_COST,
            'default_strategy': str(config.CHARGE_PRIORITY),
            'date_of_simulation': config.DATE_OF_SIMULATION,
        },
        'default_run': {k: v for k, v in base.items() if k != 'log'},
        'strategy_comparison': {k: {kk: vv for kk, vv in v.items() if kk != 'log'} for k, v in strategies.items()},
        'cloud_impact': cloud_summary,
        'seasonal_comparison': {k: {kk: vv for kk, vv in v.items() if kk != 'log'} for k, v in seasonal.items()},
    }


def main():
    parser = argparse.ArgumentParser(description='Generate simulation summary metrics as JSON.')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducible runs (default: 42)')
    parser.add_argument(
        '--output',
        type=str,
        default='',
        help='Optional output JSON file path. If omitted, prints to stdout.'
    )
    args = parser.parse_args()

    out = build_results(seed=args.seed)
    payload = json.dumps(out, indent=2)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + '\n', encoding='utf-8')
        print(f'Results written to {output_path}')
    else:
        print(payload)


if __name__ == '__main__':
    main()