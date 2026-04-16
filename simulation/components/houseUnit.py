import random

from components.battery import Battery
from components.panel import Panel
from components.inverter import Inverter
from components.grid import Grid
from components.loadModel import LoadModel
from config import (
    HOUSEHOLD_LOADS,
    WEALTH_MULTIPLIERS,
    SOLAR_ADOPTION_BY_WEALTH,
    BATTERY_ADOPTION_BY_WEALTH,
    SOLAR_SIZE_BY_WEALTH,
    BATTERY_SIZE_BY_WEALTH,
    IMPORT_COST,
    EXPORT_COST,
)


class HouseUnit:
    def __init__(self, env, weather, id, type, wealth, charge_priority,
                 has_solar=None, has_battery=None):
        self.id = id
        self.type = type
        self.wealth = wealth
        self.charge_priority = charge_priority

        # Solar / battery adoption: if not explicitly set, roll by wealth.
        # Battery adoption is conditional on having solar (realistic constraint).
        solar_prob = SOLAR_ADOPTION_BY_WEALTH.get(wealth, 0.0)
        batt_prob = BATTERY_ADOPTION_BY_WEALTH.get(wealth, 0.0)
        self.has_solar = random.random() < solar_prob if has_solar is None else bool(has_solar)
        if has_battery is None:
            self.has_battery = self.has_solar and (random.random() < batt_prob)
        else:
            self.has_battery = bool(has_battery) and self.has_solar

        self.pv_kwp = SOLAR_SIZE_BY_WEALTH.get(wealth, 5.0) if self.has_solar else 0.0
        self.batt_kwh = BATTERY_SIZE_BY_WEALTH.get(wealth, 13.5) if self.has_battery else 0.0

        self.battery = Battery(env, initial_charge=0, capacity=self.batt_kwh, enabled=self.has_battery)
        self.panel = Panel(env, self.battery, weather, peak_kw=self.pv_kwp, enabled=self.has_solar)
        self.loadModel = LoadModel(
            env,
            HOUSEHOLD_LOADS[type]["base_load"],
            HOUSEHOLD_LOADS[type]["peak_load"],
            WEALTH_MULTIPLIERS[wealth],
        )
        self.grid = Grid(env)
        self.inverter = Inverter(env, self.panel, self.battery, self.loadModel,
                                 self.grid, charge_priority)

    def dailyUpdate(self, dt):
        self.inverter.updateCondition()
        self.grid.update(dt.day)

    def stepUpdate(self, weather, dt, time_factor):
        self.panel.update(dt.hour, weather.cloud_coverage)
        self.loadModel.update(dt.hour)

        generation_kWh = self.panel.generation * time_factor
        load_kWh = self.loadModel.totalLoad * time_factor

        self.inverter.update(generation_kWh, load_kWh, time_factor)
        self.battery.update()

        grid_flow = self.inverter.last_grid_flow
        imports = -grid_flow if grid_flow < 0 else 0.0
        exports = grid_flow if grid_flow > 0 else 0.0
        # Energy the household consumed without touching the grid. Covers
        # direct solar→load AND battery→load (whose charge originally came
        # from solar). Equivalent to load_served − grid_imports.
        self_consumption_kWh = max(0.0, load_kWh - imports)

        # Cost of this tick: what we'd have paid / earned on the grid.
        tick_cost = imports * IMPORT_COST - exports * EXPORT_COST
        # Counter-factual cost (no PV/battery): everything would be imported.
        baseline_cost = load_kWh * IMPORT_COST
        tick_savings = baseline_cost - tick_cost

        return {
            "house_id": self.id,
            "type": self.type,
            "wealth": self.wealth,
            "strategy": self.charge_priority.name,
            "has_solar": self.has_solar,
            "has_battery": self.has_battery,
            "pv_kwp": self.pv_kwp,
            "batt_kwh": self.batt_kwh,
            "generation_kWh": generation_kWh,
            "load_kWh": load_kWh,
            "self_consumption_kWh": self_consumption_kWh,
            "grid_imports_kWh": imports,
            "grid_exports_kWh": exports,
            "soc": self.battery.batteryPercentage,
            "inverter_ok": not self.inverter.is_failed,
            "tick_cost": tick_cost,
            "tick_savings": tick_savings,
        }
