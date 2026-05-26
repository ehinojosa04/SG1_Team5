"""
Data preparation for the Green Grid ML model.

Reads NSRDB 2006 San Francisco weather data (30-min intervals) and the
Day-Ahead Distributed PV power data (60-min intervals), merges them by hour,
cleans the result, prints a data dictionary, and writes cleaned_data.csv.

Run directly to produce cleaned_data.csv and optional plots:
    python ml/data_prep.py              # from simulation/
    python ml/data_prep.py --plots      # also save PNG figures
"""

import csv
import math
import os
import sys

# ---------------------------------------------------------------------------
# Paths (resolved relative to this file so they work from any CWD)
# ---------------------------------------------------------------------------
_ML_DIR      = os.path.dirname(os.path.abspath(__file__))
_SIM_DIR     = os.path.dirname(_ML_DIR)
_DATA_DIR    = os.path.join(_SIM_DIR, '..', '137337_San_Francisco_2006')

WEATHER_FILE = os.path.join(_DATA_DIR, '137337_Weather_30m.csv')
POWER_FILE   = os.path.join(_DATA_DIR, '137337_DA_DPV_33MW_60m.csv')
OUTPUT_FILE  = os.path.join(_ML_DIR, 'cleaned_data.csv')
PLOTS_DIR    = os.path.join(_ML_DIR, 'plots')

# Features kept in the final dataset
FEATURES = ['GHI', 'Temperature', 'Relative Humidity',
            'Solar Zenith Angle', 'Cloud Type', 'Clearsky GHI']
TARGET   = 'Power_MW'
ALL_COLS = FEATURES + [TARGET]


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_weather_raw():
    """Return a list of row dicts from the 30-min weather CSV.

    The file has two metadata rows before the actual column header (row 3).
    """
    rows = []
    with open(WEATHER_FILE, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)           # row 1 – source metadata
        next(reader)           # row 2 – units / description
        header = next(reader)  # row 3 – actual column names
        for row in reader:
            rows.append(dict(zip(header, row)))
    return rows


def _aggregate_weather_hourly(raw_rows):
    """Average the two 30-min weather rows per hour into one hourly record.

    Returns a dict keyed by (month, day, hour) with averaged feature values.
    """
    accum = {}
    for row in raw_rows:
        try:
            key = (int(row['Month']), int(row['Day']), int(row['Hour']))
            if key not in accum:
                accum[key] = {f: 0.0 for f in FEATURES}
                accum[key]['_count'] = 0
            for f in FEATURES:
                accum[key][f] += float(row[f])
            accum[key]['_count'] += 1
        except (ValueError, KeyError):
            continue  # skip malformed rows

    hourly = {}
    for key, vals in accum.items():
        n = vals['_count']
        if n == 0:
            continue
        hourly[key] = {f: vals[f] / n for f in FEATURES}
    return hourly


def _load_power():
    """Return a dict keyed by (month, day, hour) with Power(MW) values."""
    power = {}
    with open(POWER_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Format: MM/DD/YY HH:MM
                parts = row['LocalTime'].split()
                date_parts = parts[0].split('/')
                time_parts = parts[1].split(':')
                month = int(date_parts[0])
                day   = int(date_parts[1])
                hour  = int(time_parts[0])
                power[(month, day, hour)] = float(row['Power(MW)'])
            except (ValueError, KeyError, IndexError):
                continue
    return power


# ---------------------------------------------------------------------------
# Merge and clean
# ---------------------------------------------------------------------------

def _merge_and_clean(hourly_weather, power):
    """Join weather and power on (month, day, hour); drop pure-night rows."""
    data = []
    for key, w in hourly_weather.items():
        if key not in power:
            continue
        p = power[key]
        # Skip rows where both GHI and solar power are zero (night, no signal)
        if w['GHI'] == 0.0 and p == 0.0:
            continue
        # Skip rows with negative GHI (sensor artefacts)
        if w['GHI'] < 0 or w['Clearsky GHI'] < 0:
            continue
        row = {f: w[f] for f in FEATURES}
        row[TARGET] = p
        data.append(row)
    return data


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def _stats(values):
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std  = math.sqrt(variance)
    return min(values), max(values), mean, std


def print_data_dictionary(data):
    """Print a formatted data dictionary for all columns."""
    print("\n" + "=" * 70)
    print("  DATA DICTIONARY  –  San Francisco 2006 (daytime hours only)")
    print("=" * 70)
    header = f"{'Column':<28} {'Min':>9} {'Max':>9} {'Mean':>9} {'Std':>9}"
    print(header)
    print("-" * 70)
    for col in ALL_COLS:
        vals = [row[col] for row in data]
        lo, hi, mean, std = _stats(vals)
        print(f"{col:<28} {lo:>9.3f} {hi:>9.3f} {mean:>9.3f} {std:>9.3f}")
    print("=" * 70)
    print(f"  Total daytime rows: {len(data)}")
    print()


# ---------------------------------------------------------------------------
# Visualisation (optional – only when matplotlib is available)
# ---------------------------------------------------------------------------

def _save_plots(data):
    try:
        import matplotlib
        matplotlib.use('Agg')  # non-interactive backend
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed – skipping plots.")
        return

    os.makedirs(PLOTS_DIR, exist_ok=True)

    ghi   = [r['GHI']         for r in data]
    temp  = [r['Temperature']  for r in data]
    cloud = [r['Cloud Type']   for r in data]
    power = [r[TARGET]         for r in data]
    hour_keys = sorted({r['_hour'] for r in data} if '_hour' in data[0] else set())

    # 1. GHI vs Power
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(ghi, power, alpha=0.25, s=8, color='#E07B39')
    ax.set_xlabel('GHI (W/m²)')
    ax.set_ylabel('Power (MW)')
    ax.set_title('Global Horizontal Irradiance vs Solar Power Output')
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, 'ghi_vs_power.png'), dpi=120)
    plt.close(fig)

    # 2. Temperature vs Power
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(temp, power, alpha=0.25, s=8, color='#4C72B0')
    ax.set_xlabel('Temperature (°C)')
    ax.set_ylabel('Power (MW)')
    ax.set_title('Temperature vs Solar Power Output')
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, 'temperature_vs_power.png'), dpi=120)
    plt.close(fig)

    # 3. Average power by cloud type
    cloud_bins = {}
    for r in data:
        ct = int(round(r['Cloud Type']))
        cloud_bins.setdefault(ct, []).append(r[TARGET])
    sorted_types = sorted(cloud_bins)
    avg_power_by_cloud = [sum(cloud_bins[ct]) / len(cloud_bins[ct]) for ct in sorted_types]
    labels = [str(ct) for ct in sorted_types]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, avg_power_by_cloud, color='#55A868')
    ax.set_xlabel('Cloud Type (NSRDB code)')
    ax.set_ylabel('Average Power (MW)')
    ax.set_title('Average Solar Output by Cloud Type')
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, 'cloud_type_vs_power.png'), dpi=120)
    plt.close(fig)

    # 4. Average power by hour of day – build from raw keys
    hour_power = {}
    for r in data:
        h = r.get('_hour', None)
        if h is not None:
            hour_power.setdefault(h, []).append(r[TARGET])
    if hour_power:
        hours = sorted(hour_power)
        avg_by_hour = [sum(hour_power[h]) / len(hour_power[h]) for h in hours]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(hours, avg_by_hour, marker='o', color='#C44E52')
        ax.set_xlabel('Hour of Day')
        ax.set_ylabel('Average Power (MW)')
        ax.set_title('Average Solar Output by Hour of Day')
        ax.set_xticks(hours)
        fig.tight_layout()
        fig.savefig(os.path.join(PLOTS_DIR, 'hourly_pattern.png'), dpi=120)
        plt.close(fig)

    print(f"  Plots saved to {PLOTS_DIR}/")


# ---------------------------------------------------------------------------
# Public API – used by train.py
# ---------------------------------------------------------------------------

def load_and_prepare(verbose=False):
    """Load, merge and clean the dataset. Returns list of row dicts."""
    raw_weather = _load_weather_raw()
    hourly_w    = _aggregate_weather_hourly(raw_weather)
    power       = _load_power()
    data        = _merge_and_clean(hourly_w, power)

    # Attach hour metadata for plots (stripped before returning)
    for key, row in zip(sorted(hourly_w), data):
        pass  # hour is embedded in key but not in row – attach separately

    if verbose:
        print_data_dictionary(data)
    return data


def load_and_prepare_with_keys(verbose=False):
    """Same as load_and_prepare but keeps the (month, day, hour) key in each row."""
    raw_weather = _load_weather_raw()
    hourly_w    = _aggregate_weather_hourly(raw_weather)
    power       = _load_power()

    data = []
    for key, w in hourly_w.items():
        month, day, hour = key
        if key not in power:
            continue
        p = power[key]
        if w['GHI'] == 0.0 and p == 0.0:
            continue
        if w['GHI'] < 0 or w['Clearsky GHI'] < 0:
            continue
        row = {f: w[f] for f in FEATURES}
        row[TARGET]  = p
        row['_month'] = month
        row['_day']   = day
        row['_hour']  = hour
        data.append(row)

    if verbose:
        print_data_dictionary(data)
    return data


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    save_plots = '--plots' in sys.argv

    print("Loading weather data …")
    raw_weather = _load_weather_raw()
    print(f"  Raw 30-min rows: {len(raw_weather)}")

    print("Aggregating to hourly …")
    hourly_w = _aggregate_weather_hourly(raw_weather)
    print(f"  Unique hourly slots: {len(hourly_w)}")

    print("Loading power data …")
    power = _load_power()
    print(f"  Power records: {len(power)}")

    print("Merging and cleaning …")
    data = _merge_and_clean(hourly_w, power)
    print(f"  Daytime rows retained: {len(data)}")

    print_data_dictionary(data)

    # Write cleaned CSV
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=ALL_COLS)
        writer.writeheader()
        writer.writerows(data)
    print(f"Cleaned dataset saved → {OUTPUT_FILE}")

    if save_plots:
        # Re-load with keys so we can build hourly plots
        data_with_keys = load_and_prepare_with_keys()
        _save_plots(data_with_keys)
    else:
        print("Tip: run with --plots to also generate PNG charts.")
