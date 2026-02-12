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
        gridExport = 0
        loss = 0

        status = ""
        
        match (CHARGE_PRIORITY):
            case PRIORITY_OPTIONS.LOAD:
                total = real_generation
                if load >= total:
                  status = "Insufficient input to satisfy load"

                  homeConsumption += total
                  
                  delta = load - real_generation

                  if (self.battery.level > delta):
                      status += ", pulling from battery"
                      self.battery.storage.get(delta)
                      homeConsumption += delta
                      batteryNetFlow -= delta
                
                else:
                    homeConsumption = load
                    total -= load

                    status = "Load covered"

                    if self.battery.remainingCharge > 0:
                        status += ", charging battery"
                        delta = min(total, self.battery.remainingCharge)
                        self.battery.storage.put(delta)
                        total -= delta
                        batteryNetFlow += delta
                    
                    if total > 0:
                        status += ", battery charged, exporting to grid"
                        delta = min(GRID_CONSTRAINT, total)
                        gridExport = delta
                        total -= delta
                        loss += total

        
        print(f"Inverter update: {status}. Home consumption: {homeConsumption} | Battery net flow: {batteryNetFlow} | Grid export: {gridExport} | Loss: {loss}")