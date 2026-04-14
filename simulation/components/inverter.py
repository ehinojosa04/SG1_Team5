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

    def update(self, generation, load, time_factor):
        if self.is_failed:
            self.total_downtime += time_factor
            self.downtime_remaining -= time_factor
            if self.downtime_remaining <= 0: 
                self.is_failed = False
                self.downtime_remaining = 0
            
            self.metrics["total_grid_import"] += load
            self.metrics["unmet_load_events"] += 1
            self.last_grid_flow = -load
            return

        max_inverter_kWh = INVERTER_CLIPPING * time_factor
        real_gen = min(generation, max_inverter_kWh)
        self.metrics["total_solar_gen"] += real_gen
        
        home_served = 0.0
        battery_flow = 0.0
        grid_flow = 0.0
        loss = 0.0

        if self.priority == PRIORITY_OPTIONS.LOAD:
            # POWER THE HOUSE FIRST
            solar_to_home = min(load, real_gen)
            home_served = solar_to_home
            remaining_gen = real_gen - solar_to_home
            remaining_load = load - solar_to_home
            
            # IF MORE IS NEEDED, PULL FROM THE BATTERY
            if remaining_load > 0.001:
                real_need = remaining_load / ROUND_TRIP_EFFICIENCY
                battery_draw = min(real_need, self.battery.level)
                
                if battery_draw > 0.001:
                    self.battery.storage.get(battery_draw)
                    useful_energy = battery_draw * ROUND_TRIP_EFFICIENCY
                    
                    battery_flow -= useful_energy
                    home_served += useful_energy
                    remaining_load -= useful_energy 

            # IF MORE IS NEEDED, PULL FROM THE GRID
            if remaining_load > 0.001: 
                grid_flow -= remaining_load
                home_served += remaining_load

            # IF ENERGY LEFT, CHARGE THE BATTERY
            if remaining_gen > 0.001:
                energy_to_store = remaining_gen * ROUND_TRIP_EFFICIENCY
                
              
                real_store = min(self.battery.remainingCharge , energy_to_store)
                
                if real_store > 0.001:
                    self.battery.storage.put(real_store)
                   
                    energy_cost = real_store / ROUND_TRIP_EFFICIENCY
                    battery_flow += real_store
                    remaining_gen -= energy_cost 

           # IF ENERGY LEFT AND BATTERY IS FULL, EXPORT TO THE GRID
            if remaining_gen > 0.001:
                export = min(self.grid.remainingExport, remaining_gen)
                if export > 0:
                    self.grid.exportLimit.put(export)
                grid_flow += export
                loss = remaining_gen - export
       
        elif self.priority == PRIORITY_OPTIONS.CHARGE:
            energy_to_store = real_gen * ROUND_TRIP_EFFICIENCY
            real_store = min(self.battery.remainingCharge, energy_to_store)
            
            if real_store > 0.001:
                self.battery.storage.put(real_store)
                energy_cost = real_store / ROUND_TRIP_EFFICIENCY
                battery_flow += real_store
                real_gen -= energy_cost 

           
            solar_to_home = min(load, real_gen)
            home_served = solar_to_home
            remaining_gen = real_gen - solar_to_home
            remaining_load = load - solar_to_home
            
            if remaining_load > 0.001: 
                grid_flow -= remaining_load
                home_served += remaining_load

            if remaining_gen > 0.001:
                export = min(self.grid.remainingExport, remaining_gen)
                if export > 0:
                    self.grid.exportLimit.put(export)
                grid_flow += export
                loss = real_gen - export

        elif self.priority == PRIORITY_OPTIONS.PRODUCE:
            # EXPORT ENERGY GENERATED TO THE GRID
            solar_to_grid = min(self.grid.remainingExport, real_gen)
            remaining_gen = real_gen

            if solar_to_grid > 0 and self.grid.remainingExport > 0:
                self.grid.exportLimit.put(solar_to_grid)
                grid_flow += solar_to_grid
                remaining_gen -= solar_to_grid

            # IF ENERGY REMAINING, CHARGE THE BATTERY
            if remaining_gen > 0.001:
                energy_to_store = remaining_gen * ROUND_TRIP_EFFICIENCY
                real_store = min(self.battery.remainingCharge, energy_to_store)

                if real_store > 0.001: 
                    self.battery.storage.put(real_store)
                    energy_cost = real_store / ROUND_TRIP_EFFICIENCY
                    battery_flow += real_store
                    remaining_gen -= energy_cost
            
            # SATISFY LOAD WITH ENERGY REMAINING, 
            solar_to_home = min(load, remaining_gen)
            home_served = solar_to_home
            remaining_gen -= home_served
            remaining_load = load - home_served

            # IF ENERGY REMAINING, PULL FROM THE GRID
            if remaining_load > 0.001:
                grid_flow -= remaining_load
                home_served += remaining_load
            
            loss = remaining_gen
            
            

        self.metrics["total_load_served"] += home_served
        if grid_flow > 0: self.metrics["total_grid_export"] += grid_flow
        else: self.metrics["total_grid_import"] += abs(grid_flow)
        self.metrics["total_losses"] += loss
        self.last_grid_flow = grid_flow