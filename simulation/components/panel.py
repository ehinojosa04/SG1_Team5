from simpy import Environment
import math
from components.battery import Battery
from components.weather import Weather
from config import MINUTES_PER_TICK, SOLAR_PEAK

class Panel:
    def __init__(self, env: Environment, battery: Battery, weather: Weather):
        self.env = env
        self.battery = battery
        self.weather = weather
        self.generation = 0

    def update(self, cloudCoverage):
        sun_angle = (self.env.now % 24 - 6) * (math.pi / 12)
#        self.generation = max(0, SOLAR_PEAK * math.sin(sun_angle) * (1-cloudCoverage))
        self.generation = max(0, SOLAR_PEAK * math.sin(sun_angle))
        print(f"Panel update: {self.generation:.2f} kW generated")