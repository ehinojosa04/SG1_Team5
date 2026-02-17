from simpy import Environment, Container
from config import BATTERY_CAPACITY, BATTERY_FLOOR, MINUTES_PER_TICK

class Battery:
    def __init__(self, env, initial_charge, capacity=BATTERY_CAPACITY):
        self.env: Environment = env
        self.capacity = capacity
        self.storage = Container(env, self.capacity, initial_charge)
    
    def update(self):
        print(f"Battery update: {self.batteryPercentage:.2f}% | {self.storage.level:.2f} Wh")

    @property
    def level(self):
        return self.storage.level

    @property
    def batteryPercentage(self):
        return (self.storage.level / self.capacity) * 100 if self.capacity > 0 else 0
    
    @property
    def remainingCharge(self):
        return self.capacity - self.storage.level