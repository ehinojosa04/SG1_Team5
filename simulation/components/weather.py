import math
from simpy import Environment
import random

class Weather:
    def __init__(self, env: Environment):
        self.env = env
        self.cloud_coverage = 0

    def update(self):
        self.cloud_coverage = random.randint(0, 10)/10
        print(f"Weather update: Cloud coverage is now {self.cloud_coverage}")