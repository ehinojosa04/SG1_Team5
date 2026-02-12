from config import BASE_LOAD, MINUTES_PER_TICK

class Home:
    def __init__(self, env) -> None:
        self.env = env
        self.baseLoad = BASE_LOAD

        self.totalLoad = 0

    def update(self):
        self.totalLoad = self.baseLoad # + some random calculation
        print(f"House update: load is now {self.totalLoad}")

    @property
    def load(self):
        return self.baseLoad
