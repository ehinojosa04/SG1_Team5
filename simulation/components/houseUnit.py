from simpy import Environment
from config import *

from components.battery import Battery
from components.panel import Panel
from components.weather import Weather
from components.inverter import Inverter
from components.grid import Grid
from components.loadModel import LoadModel

class HouseUnit:
    def __init__(self, env, id, type, wealth, charge_priority):
        self.id = id
        self.battery = Battery(env, initial_charge=0, capacity=BATTERY_CAPACITY)
        self.weather = Weather(env)
        self.panel = Panel(env, self.battery, self.weather)
        self.loadModel = LoadModel(env, HOUSEHOLD_LOADS[type]['base_load'], HOUSEHOLD_LOADS[type]['peak_load'], WEALTH_MULTIPLIERS[wealth])
        self.grid = Grid(env)
        self.inverter = Inverter(env, self.panel, self.battery, self.loadModel, self.grid, charge_priority)

