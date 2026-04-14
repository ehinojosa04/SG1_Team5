from simpy import Environment
from config import *

from components.battery import Battery
from components.panel import Panel
from components.weather import Weather
from components.inverter import Inverter
from components.grid import Grid
from components.loadModel import LoadModel

class HouseUnit:
    def __init__(self, env, weather, id, type, wealth, charge_priority):
        self.id = id
        self.type = type
        self.wealth = wealth
        self.charge_priority = charge_priority

        self.battery = Battery(env, initial_charge=0, capacity=BATTERY_CAPACITY)
        self.panel = Panel(env, self.battery, weather)
        self.loadModel = LoadModel(env, HOUSEHOLD_LOADS[type]['base_load'], HOUSEHOLD_LOADS[type]['peak_load'], WEALTH_MULTIPLIERS[wealth])
        self.grid = Grid(env)
        self.inverter = Inverter(env, self.panel, self.battery, self.loadModel, self.grid, charge_priority)

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

        return {
            "house_id": self.id,
            "type": self.type,
            "wealth": self.wealth,
            "generation_kWh": generation_kWh,
            "load_kWh": load_kWh,
            "soc": self.battery.batteryPercentage,
            "grid_imports_kWh": abs(self.inverter.last_grid_flow) if self.inverter.last_grid_flow < 0 else 0,
            "grid_exports_kWh": abs(self.inverter.last_grid_flow) if self.inverter.last_grid_flow > 0 else 0,
            "inverter_ok": not self.inverter.is_failed
        }