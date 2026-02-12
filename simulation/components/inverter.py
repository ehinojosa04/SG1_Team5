from simpy import Environment
from components.battery import Battery
from components.panel import Panel
from components.home import Home
from components.grid import Grid

from config import INVERTER_CLIPPING, CHARGE_PRIORITY, PRIORITY_OPTIONS, MINUTES_PER_TICK, GRID_CONSTRAINT
import math

class Inverter:
    def __init__(self, env, panel, battery, home, grid) -> None:
        self.env: Environment = env

        self.panel:Panel = panel
        self.battery: Battery = battery
        self.home = home
        self.grid: Grid = grid

    def update(self, generation, load):
        real_generation = min(self.panel.generation, INVERTER_CLIPPING)
        
        homeConsumption = 0
        batteryNetFlow = 0
        gridNetFlow = 0
        loss = 0

        status = ""
        
        match (CHARGE_PRIORITY):
            case PRIORITY_OPTIONS.LOAD:
                solar_to_home = min(load, real_generation)
                remaining_solar = real_generation - solar_to_home
                remaining_load = load - solar_to_home
                
                homeConsumption = solar_to_home

                if remaining_load > 0:
                    battery_to_home = min(load, self.battery.level)
                    if battery_to_home > 0:
                        self.battery.storage.get(battery_to_home)
                        
                        batteryNetFlow -= battery_to_home
                        
                        homeConsumption += battery_to_home

                        remaining_load -= battery_to_home

                    if remaining_load > 0:
                        gridNetFlow -= remaining_load
                        homeConsumption += remaining_load
                
                else:
                    homeConsumption = load

                    if remaining_solar > 0:
                        battery_charge = min(self.battery.remainingCharge, remaining_solar)
                        if battery_charge > 0:
                            self.battery.storage.put(battery_charge)
                            batteryNetFlow += battery_charge

                            remaining_solar -= battery_charge

                    if remaining_solar > 0:
                        gridNetFlow += min(GRID_CONSTRAINT, remaining_solar)
                        loss = remaining_solar - gridNetFlow

                    

        
        print(f"Inverter update: {status}. Home consumption: {homeConsumption:.2f} | Battery net flow: {batteryNetFlow:.2f} | Grid net flow: {gridNetFlow:.2f} | Loss: {loss:.2f}")