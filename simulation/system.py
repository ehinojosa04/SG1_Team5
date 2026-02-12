from simpy import Environment
from config import MINUTES_PER_TICK, SIMULATION_DAYS

from components.battery import Battery
from components.panel import Panel
from components.weather import Weather
from components.inverter import Inverter
from components.grid import Grid
from components.home import Home

import math

def Simulate(env: Environment, weather: Weather, panel: Panel, home: Home, inverter: Inverter, battery: Battery, grid: Grid):
    while True:
        yield env.timeout(MINUTES_PER_TICK / 60)
        print("----------------------------")
        print(f"Time: Day {env.now//24} {math.floor(env.now%24)} hrs {((env.now%24)%1) * 60} mins")
        weather.update()
        panel.update(weather.cloud_coverage)
        home.update()
        inverter.update(panel.generation, home.totalLoad)
        battery.update()
        grid.update()

def main() -> None:
    env = Environment()

    battery = Battery(env, initial_charge=0)
    weather = Weather(env)
    panel = Panel(env, battery, weather)
    home = Home(env)
    grid = Grid()

    inverter = Inverter(env, panel, battery, home, grid)

    env.process(Simulate(env, weather, panel, home, inverter, battery, grid))

    duration = SIMULATION_DAYS * 24
    print(f"Starting simulation for {duration} hours")
    env.run(until=duration)
    
if __name__ == '__main__':
    main()