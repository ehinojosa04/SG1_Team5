from simpy import Environment
import math
from components.battery import Battery
from components.weather import Weather
from config import SOLAR_PEAK


class Panel:
    def __init__(self, env: Environment, battery: Battery, weather: Weather,
                 peak_kw: float = SOLAR_PEAK, enabled: bool = True):
        self.env = env
        self.battery = battery
        self.weather = weather
        self.peak_kw = peak_kw if enabled else 0.0
        self.enabled = bool(enabled) and peak_kw > 0
        self.generation = 0.0

    def update(self, hour, cloudCoverage):
        if not self.enabled:
            self.generation = 0.0
            return
        sun_angle = (hour - 6) * (math.pi / 12)
        self.generation = max(0.0, self.peak_kw * math.sin(sun_angle) * (1 - cloudCoverage))
