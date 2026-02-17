from config import GRID_CONSTRAINT
from simpy import Container

class Grid:
    def __init__(self, env):
        self.exportLimit = Container(env, GRID_CONSTRAINT)

    def update(self, day):
        if day == 1:
            self.exportLimit.get(self.exportLimit.level)

    @property
    def remainingExport(self):
        return self.exportLimit.capacity - self.exportLimit.level