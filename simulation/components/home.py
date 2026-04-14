from config import BASE_LOAD, APPLIANCES, MAX_PEAK_LOAD, PEAK_USAGE_HOUR_START, PEAK_USAGE_HOUR_END
import random

import random

class Appliance:
    def __init__(self, name: str, power_kW: float, usage_probabilities: dict):
        self.name = name
        self.power_kW = power_kW
        self.usage_probabilities = usage_probabilities 
        self.is_on = False

    def check_usage(self, current_hour: int) -> float:
        prob = self.usage_probabilities.get(current_hour, 0.0)
        self.is_on = random.random() < prob
        
        return self.power_kW if self.is_on else 0.0

class Home:
    def __init__(self, env) -> None:
        self.env = env
        self.totalLoad = 0
        self.appliances = []

        for a in APPLIANCES:
            self.appliances.append(
                Appliance(a['name'], a['power_kW'], a['usage'])
            )

        self.appliances.sort(key=lambda x: x.power_kW)

    def update(self, t):
        currentLoad = BASE_LOAD

        for appliance in self.appliances:
            if currentLoad + appliance.power_kW > MAX_PEAK_LOAD:
                continue 

            currentLoad += appliance.check_usage(t)

        self.totalLoad = currentLoad
        #print(f"House update: load is now {self.totalLoad}")

    @property
    def load(self):
        return self.totalLoad