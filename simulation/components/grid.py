from config import GRID_CONSTRAINT, MINUTES_PER_TICK


class Grid:
    """Per-household grid connection.

    GRID_CONSTRAINT is an *instantaneous* power cap in kW (e.g. the inverter's
    feed-in limit for this house). Each tick the household may export at most
    GRID_CONSTRAINT × tick_hours kWh to the grid; the budget resets every tick.
    """

    def __init__(self, env):
        self.env = env
        self.per_tick_export_kwh = GRID_CONSTRAINT * (MINUTES_PER_TICK / 60)

    def update(self, day):
        # Kept for backwards compatibility with HouseUnit.dailyUpdate.
        pass

    @property
    def remainingExport(self):
        return self.per_tick_export_kwh
