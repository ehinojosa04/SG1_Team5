from simpy import Environment, Container
from config import BATTERY_CAPACITY, BATTERY_FLOOR, EFFICIENCY, MINUTES_PER_TICK
import math

class Battery:
    def __init__(self, env, initial_charge):
        self.env : Environment = env
        self.storage = Container(env, BATTERY_CAPACITY, initial_charge)
        self.netFlow = 0
        self.min_charge_limit = BATTERY_CAPACITY * BATTERY_FLOOR
    
    def update(self):
        print(f"Battery update: {self.batteryPercentage:.2f}% | {self.storage.level:.2f} kWh")

    @property
    def availableEnergy(self):
        return max(0, self.level - self.min_charge_limit)

    @property
    def level(self):
        return self.storage.level

    @property
    def batteryPercentage(self):
        return (self.storage.level / BATTERY_CAPACITY) * 100
    
    @property
    def remainingCharge(self):
        return BATTERY_CAPACITY - self.storage.level