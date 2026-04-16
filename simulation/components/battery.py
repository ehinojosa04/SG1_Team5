from simpy import Environment, Container
from config import BATTERY_CAPACITY

# SimPy Container does not accept capacity == 0, so disabled batteries use a
# capacity well below the inverter's 0.001 kWh activity threshold. This keeps
# downstream logic identical ("nothing ever fits") without special-casing.
_DISABLED_CAPACITY = 1e-9


class Battery:
    def __init__(self, env, initial_charge, capacity=BATTERY_CAPACITY, enabled=True):
        self.env: Environment = env
        self.enabled = bool(enabled) and capacity > 0
        self.nominal_capacity = capacity if self.enabled else 0.0
        storage_capacity = capacity if self.enabled else _DISABLED_CAPACITY
        self.storage = Container(env, storage_capacity, initial_charge if self.enabled else 0)

    def update(self):
        pass

    @property
    def capacity(self):
        return self.nominal_capacity

    @property
    def level(self):
        return self.storage.level if self.enabled else 0.0

    @property
    def batteryPercentage(self):
        if not self.enabled or self.nominal_capacity <= 0:
            return 0.0
        return (self.storage.level / self.nominal_capacity) * 100

    @property
    def remainingCharge(self):
        if not self.enabled:
            return 0.0
        return self.nominal_capacity - self.storage.level
