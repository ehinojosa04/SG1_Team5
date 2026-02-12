import math
from simpy import Environment
import random
from datetime import datetime
from config import SEASON_PROBABILITY_FACTOR, CLOUD_COVERAGE, WEATHER_TYPES

class Weather:
    def __init__(self, env: Environment):
        self.env = env
        self.cloud_coverage = 0
        self.weather = ""

    def update(self, date: datetime):
        month = date.month
        season = "WINTER" if month in (12, 1, 2) else "SPRING" if month in (3, 4, 5) else "SUMMER" if month in (6, 7, 8) else "FALL"
        
        self.weather = random.choices(
            population=WEATHER_TYPES,
            weights=SEASON_PROBABILITY_FACTOR[season],
            k=1
        )[0]

        min_c, max_c = CLOUD_COVERAGE[self.weather]
        self.cloud_coverage = random.uniform(min_c, max_c)