# Green Grid Digital Twin — SG1 Team 5

A discrete-event simulation of a **residential neighborhood** of solar-powered
homes with batteries and grid interaction, plus an interactive **Streamlit
dashboard** that tells the adoption / savings story.

The simulator models ~100 households with different archetypes (studio,
small, large), wealth levels (low → luxury), probabilistic solar/battery
adoption, and stochastic appliance-level consumption — all driven by
season-aware weather. A data pipeline automatically transforms the raw
tick-level output into dashboard-ready datasets, and the dashboard
visualises production vs. consumption, the duck curve, economics, adoption
rates, battery utilisation and more — all filterable by type, wealth,
strategy and time granularity (day / week / month / quarter / year).

## Project structure

```
SG1_Team5/
├── README.md
├── requirements.txt
├── simulation/
│   ├── simulation.py              # Neighborhood simulator entry point
│   ├── data_pipeline.py           # Auto-runs at end of sim; publishes to dashboard/data/
│   ├── config.py                  # Tunable parameters + named scenarios
│   ├── config.template.py         # Reference template
│   ├── output/                    # Raw tick-level CSVs (generated)
│   └── components/                # Battery, Panel, Inverter, Grid, LoadModel, HouseUnit, Weather
└── dashboard/
    ├── app.py                     # Streamlit + Plotly dashboard
    └── data/                      # Dashboard-ready CSVs (generated, transparently populated)
```

## Prerequisites

- Python **3.10+** (tested with 3.13)
- `pip`

## Setup

```bash
git clone https://github.com/ehinojosa04/SG1_Team5
cd SG1_Team5

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

`requirements.txt` installs `simpy`, `pandas`, `streamlit`, and `plotly`.

## Running the simulator

All simulation commands run from the `simulation/` directory so local imports
resolve correctly.

```bash
cd simulation
python simulation.py
```

This will:

1. Instantiate the neighborhood defined in `config.py`
   (`NEIGHBORHOOD_CONFIG` + probabilistic solar/battery adoption per wealth).
2. Run `SIMULATION_DAYS` (default **30**) at `MINUTES_PER_TICK` resolution
   (default **15 min**) — every household simulates its own PV, battery,
   inverter, grid connection, and appliance-level load each tick.
3. Write raw tick-level CSVs to `simulation/output/`:
   - `HouseholdsSummary.csv` — one row per (timestamp, household)
   - `SystemSummary.csv` — neighborhood aggregates per tick
   - `HouseholdsMeta.csv` — static household metadata (type, wealth, sizes,
     `has_solar`, `has_battery`, strategy)
4. **Automatically run the data pipeline** (`data_pipeline.py`), which
   transforms these raw files into dashboard-ready datasets and writes them
   to `dashboard/data/`. No manual file moving required — the dashboard
   immediately picks up the new run.

### Selecting a scenario

Three named scenarios are defined in `config.py` under `SCENARIOS`. Switch
between them with the `GG_SCENARIO` environment variable — a single config
that can run all household types and wealth levels in one go, just with
different adoption probabilities:

```bash
GG_SCENARIO=baseline        python simulation.py    # default
GG_SCENARIO=high_adoption   python simulation.py    # most homes have solar+battery
GG_SCENARIO=low_adoption    python simulation.py    # pre-incentives world
```

You can add your own scenario by extending the `SCENARIOS` dict in
`config.py` (custom neighborhood mix and/or adoption probabilities).

For fully independent configurations, copy `config.template.py` alongside
`config.py`, tweak, and point Python at it by setting `PYTHONPATH`
accordingly — or just edit the values directly in `config.py`.

### Re-running just the pipeline

If you already have a fresh `simulation/output/` and only want to rebuild
the dashboard datasets:

```bash
cd simulation
python data_pipeline.py
```

## Running the dashboard

From the repository root:

```bash
streamlit run dashboard/app.py
```

Streamlit opens the dashboard at <http://localhost:8501>. Features:

- **Sidebar**
  - Scenario selector + one-click **Run simulation** button (launches the
    simulator as a subprocess with the chosen scenario, then reloads).
  - Multi-select filters: household type, wealth level, charge strategy.
  - Solar / battery filters (`All` / `Only solar` / `Only non-solar`, etc.).
  - Date range picker.
  - Time granularity selector (Hour / Day / Week / Month / Quarter / Year).
- **Tabs**
  1. **Overview** — KPIs + production vs. consumption + surplus/deficit.
  2. **Duck Curve** — classic net-load vs. hour-of-day curve, grouped by
     neighborhood / type / wealth.
  3. **By Type** — bar, box and heatmap breakdowns per household archetype.
  4. **By Wealth** — production vs. consumption and net-$ heatmap by
     wealth × type.
  5. **Economics** — cumulative savings over time, per-household savings
     distribution, winners & losers by segment.
  6. **Adoption** — solar and battery adoption heatmaps + scatter of
     adoption vs. per-home savings.
  7. **Battery & Grid** — SoC by hour of day, grid imports/exports by
     hour, peak demand vs. peak production annotations.

### Public hosting (optional)

Streamlit apps deploy for free to
[Streamlit Community Cloud](https://streamlit.io/cloud):

1. Push this repository to GitHub.
2. Connect your GitHub account on share.streamlit.io.
3. Point it at `dashboard/app.py`.
4. Add `requirements.txt` to the app settings.

Because the pipeline writes relative to the project root, the dashboard
works out of the box on Streamlit Cloud as long as the repo is checked
out with a pre-generated `dashboard/data/` (commit a baseline run or
generate one on startup).

## Key configuration

All parameters in `simulation/config.py` are documented inline. Headlines:

| Parameter | Purpose |
|---|---|
| `SIMULATION_DAYS`, `MINUTES_PER_TICK`, `DATE_OF_SIMULATION` | Time |
| `HOUSEHOLD_LOADS` | base/peak load per type |
| `WEALTH_MULTIPLIERS` | consumption multiplier per wealth level |
| `SOLAR_ADOPTION_BY_WEALTH`, `BATTERY_ADOPTION_BY_WEALTH` | adoption probabilities |
| `SOLAR_SIZE_BY_WEALTH`, `BATTERY_SIZE_BY_WEALTH` | PV/battery sizing per wealth |
| `NEIGHBORHOOD_CONFIG` | (type, wealth, strategy, count) groups — 100 households total |
| `SCENARIOS` | named bundles of neighborhood + adoption, selectable via `GG_SCENARIO` |
| `PRIORITY_OPTIONS` | `LOAD`, `CHARGE`, `PRODUCE` energy dispatch strategies |
| `IMPORT_COST`, `EXPORT_COST` | grid tariff in $/kWh |
| `RANDOM_SEED` | reproducibility (set to `None` for nondeterministic runs) |

## Outputs glossary

Written by `simulation/data_pipeline.py` to `dashboard/data/`:

| File | Contents |
|---|---|
| `ticks.csv` | One row per (timestamp, household) with derived time & net-kWh columns |
| `system.csv` | Neighborhood totals per tick |
| `households.csv` | Static metadata per household |
| `daily_by_household.csv` | Daily rollup per household |
| `hourly_by_segment.csv` | Hour-of-day × (type, wealth) means — feeds duck curve |
| `hourly_neighborhood.csv` | Hour-of-day means across the whole neighborhood |
| `segment_summary.csv` | (type × wealth) totals for the run |
| `adoption.csv` | Solar/battery adoption counts and % per segment |
| `manifest.json` | Run metadata (scenario, generated_at, tariffs, time range) |

## Troubleshooting

- **Dashboard shows "No data available yet"**: run the simulator first
  (`cd simulation && python simulation.py`) or click **Run simulation** in
  the sidebar.
- **Scenario change doesn't take effect**: the dashboard's Run-simulation
  button passes `GG_SCENARIO` to a subprocess; make sure no cached Python
  has imported `config` in an ambient shell.
- **Charts are empty after filtering**: filters intersect — loosen the
  solar/battery/strategy filters first.

## Deactivating the virtual environment

```bash
deactivate
```
