# Green Grid Digital Twin - SG1 Team 5

A discrete-event simulation of a residential solar energy system with battery storage and grid interaction. The simulator models solar panel generation, household energy consumption, battery charge/discharge cycles, inverter behavior (including random failures), and grid import/export — all driven by weather conditions that vary by season.

## Project Structure

```
SG1_Team5/
├── README.md
├── requirements.txt
└── simulation/
    ├── system.py              # Main simulation engine (30-day run)
    ├── compare_strats.py      # Runs and compares three energy strategies
    ├── config.py              # Simulation configuration (tunable parameters)
    ├── Monthly_Summary.csv    # Output: hourly simulation log (generated)
    └── components/
        ├── battery.py         # Battery storage model (SimPy Container)
        ├── grid.py            # Grid connection model
        ├── home.py            # Household load model
        ├── inverter.py        # Inverter and energy management logic
        ├── panel.py           # Solar panel generation model
        └── weather.py         # Weather and cloud coverage model
```

## Prerequisites

- **Python 3.10+** (tested with Python 3.13)
- **pip** (Python package manager)

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ehinojosa04/SG1_Team5
cd SG1_Team5
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

> On **Windows**, activate with: `venv\Scripts\activate`

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:

| Package | Purpose |
|---------|---------|
| `simpy` | Discrete-event simulation framework |

All other imports (`csv`, `datetime`, `math`, `random`) are part of the Python standard library.

### 4. Configure the Simulation

All tunable parameters live in `simulation/config.py`. Open the file and adjust values to match your scenario. Every parameter is documented with inline comments. Key settings include:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BATTERY_CAPACITY` | `13500` Wh | Total battery storage capacity |
| `SOLAR_PEAK` | `5000` W | Peak solar panel output |
| `BASE_LOAD` | `500` W | Constant household consumption |
| `CHARGE_PRIORITY` | `LOAD` | Active energy management strategy (`LOAD`, `CHARGE`, or `PRODUCE`) |
| `SIMULATION_DAYS` | `30` | Number of days to simulate |
| `DATE_OF_SIMULATION` | `01/05/2026` | Start date (dd/mm/yyyy) |

See `simulation/config.py` for the full list of parameters.

## Running the Simulation

All commands must be run from the `simulation/` directory so that Python can resolve the local imports correctly.

```bash
cd simulation
```

### Run the Main Simulation

```bash
python system.py
```

This will:
- Simulate 30 days of solar generation, household consumption, and battery/grid interaction
- Print a technical report with key metrics (SoC, solar output, load, inverter failures, economics)
- Generate `Monthly_Summary.csv` with hourly data

**Sample output:**

```
--- GREEN GRID DIGITAL TWIN | INICIANDO SIMULACIÓN MENSUAL ---

=======================================================
        TECHNICAL REPORT - SIMULATION SUMMARY (30 DAYS)
=======================================================
1. Average Monthly SoC:           XX.XX%
2. Hours Battery Full:            XX hrs
3. Hours Battery Empty:           XX hrs
4. Total Solar Energy:            XX.XX kWh
5. Total Household Consumption:   XX.XX kWh
6. Inverter Failures:             X events
7. Total Downtime:                X hrs
8. Average Cloud Coverage:        X.XX
9. Peak Load Demand:              XXX.XX W
10. Unmet Load Events:            X
-------------------------------------------------------
>> ECONOMIC BALANCE: XX.XX cents
   (Cost: -XX.XX | Credit: +XX.XX)
=======================================================
```

### Run the Strategy Comparison

```bash
python compare_strats.py
```

This will:
- Run three independent simulations, one for each energy management strategy:
  - **LOAD PRIORITY** — serve household load first, then charge battery, then export surplus
  - **CHARGE PRIORITY** — charge battery first, then serve load
  - **PRODUCE PRIORITY** — export to grid first, then charge battery, then serve load
- Print a comparison table and identify the most cost-effective strategy

## Output Files

| File | Description |
|------|-------------|
| `Monthly_Summary.csv` | Hourly log with columns: `Timestamp`, `Solar_Wh`, `House_Load_Wh`, `SoC_%`, `Grid_Net_Wh`, `Cloud_Cov`, `Inverter_OK` |

## Deactivating the Virtual Environment

When you are done, deactivate the virtual environment:

```bash
deactivate
```
