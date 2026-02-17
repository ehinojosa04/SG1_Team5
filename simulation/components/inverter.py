import random
from components.grid import Grid
from config import (PRIORITY_OPTIONS, GRID_CONSTRAINT, INVERTER_CLIPPING, 
                    INVERTER_FAIL_PROB, MIN_INVERTER_FAIL_DURATION, MAX_INVERTER_FAIL_DURATION, ROUND_TRIP_EFFICIENCY, MINUTES_PER_TICK)

class Inverter:
    def __init__(self, env, panel, battery, home, grid: Grid, priority):
        self.env = env
        self.panel, self.battery, self.home, self.grid = panel, battery, home, grid
        self.priority = priority
        
        self.is_failed = False
        self.downtime_remaining = 0
        self.fail_count = 0
        self.total_downtime = 0
        
        self.last_grid_flow = 0.0
        self.metrics = {
            "total_solar_gen": 0.0, "total_load_served": 0.0,
            "total_grid_export": 0.0, "total_grid_import": 0.0,
            "total_losses": 0.0, "unmet_load_events": 0
        }

    def updateCondition(self):
        if not self.is_failed and random.random() < INVERTER_FAIL_PROB:
            self.is_failed = True
            self.fail_count += 1
            self.downtime_remaining = random.randint(MIN_INVERTER_FAIL_DURATION, MAX_INVERTER_FAIL_DURATION)

    def update(self, generation, load):
        if self.is_failed:
            self.total_downtime += MINUTES_PER_TICK / 60
            self.downtime_remaining -= MINUTES_PER_TICK / 60
            if self.downtime_remaining <= 0: 
                self.is_failed = False
                self.downtime_remaining = 0
            
            self.metrics["total_grid_import"] += load
            self.metrics["unmet_load_events"] += 1
            self.last_grid_flow = -load
            return

        real_gen = min(generation, INVERTER_CLIPPING)
        self.metrics["total_solar_gen"] += real_gen
        
        home_served = 0.0
        batt_flow = 0.0
        grid_flow = 0.0
        loss = 0.0

        if self.priority == PRIORITY_OPTIONS.LOAD:
            solar_to_home = min(load, real_gen)
            home_served = solar_to_home
            rem_gen = real_gen - solar_to_home
            rem_load = load - solar_to_home
            
            if rem_load > 0.001:
                necesidad_real = rem_load / ROUND_TRIP_EFFICIENCY
                sacar_de_batt = min(necesidad_real, self.battery.level)
                
                if sacar_de_batt > 0.001:
                    self.battery.storage.get(sacar_de_batt)
                    energia_util = sacar_de_batt * ROUND_TRIP_EFFICIENCY
                    
                    batt_flow -= energia_util
                    home_served += energia_util
                    rem_load -= energia_util 

  
            if rem_load > 0.001: 
                grid_flow -= rem_load
                home_served += rem_load

            if rem_gen > 0.001:
                espacio_libre = self.battery.remainingCharge 
        
                energia_a_guardar = rem_gen * ROUND_TRIP_EFFICIENCY
                
              
                guardar_real = min(espacio_libre, energia_a_guardar)
                
                if guardar_real > 0.001:
                    self.battery.storage.put(guardar_real)
                   
                    costo_panel = guardar_real / ROUND_TRIP_EFFICIENCY
                    batt_flow += guardar_real
                    rem_gen -= costo_panel 

           
                if rem_gen > 0.001:
                    export = min(self.grid.remainingExport, rem_gen)
                    if export > 0:
                        self.grid.exportLimit.put(export)
                    grid_flow += export
                    loss = rem_gen - export
       
        elif self.priority == PRIORITY_OPTIONS.CHARGE:
           
            energia_a_guardar = real_gen * ROUND_TRIP_EFFICIENCY
            guardar_real = min(self.battery.remainingCharge, energia_a_guardar)
            
            if guardar_real > 0.001:
                self.battery.storage.put(guardar_real)
                costo_panel = guardar_real / ROUND_TRIP_EFFICIENCY
                batt_flow += guardar_real
                real_gen -= costo_panel 

           
            solar_to_home = min(load, real_gen)
            home_served = solar_to_home
            rem_load = load - solar_to_home
            
            if rem_load > 0.001: 
                grid_flow -= rem_load
                home_served += rem_load

        elif self.priority == PRIORITY_OPTIONS.PRODUCE:
            solar_to_home = min(load, real_gen)
            home_served = solar_to_home
            rem_gen = real_gen - solar_to_home
            rem_load = load - solar_to_home 
            
            export = min(GRID_CONSTRAINT, rem_gen)
            grid_flow += export
            rem_gen -= export
            
            if rem_gen > 0.001:
                energia_a_guardar = rem_gen * ROUND_TRIP_EFFICIENCY
                guardar_real = min(self.battery.remainingCharge, energia_a_guardar)
                if guardar_real > 0.001: 
                    self.battery.storage.put(guardar_real)
                    batt_flow += guardar_real
            
            if rem_load > 0.001: 
                grid_flow -= rem_load
                home_served += rem_load

        self.metrics["total_load_served"] += home_served
        if grid_flow > 0: self.metrics["total_grid_export"] += grid_flow
        else: self.metrics["total_grid_import"] += abs(grid_flow)
        self.metrics["total_losses"] += loss
        self.last_grid_flow = grid_flow