from config import BASE_LOAD, MINUTES_PER_TICK, MAX_PEAK_LOAD, PEAK_USAGE_HOUR_START, PEAK_USAGE_HOUR_END
from datetime import datetime
import random

class Home:
    def __init__(self, env) -> None:
        self.env = env
        self.totalLoad = 0

    def update(self, t):
        self.totalLoad = BASE_LOAD if t < PEAK_USAGE_HOUR_START or t > PEAK_USAGE_HOUR_END else random.randint(BASE_LOAD, MAX_PEAK_LOAD)
        print(f"House update: load is now {self.totalLoad}")

    @property
    def load(self):
        return self.totalLoad