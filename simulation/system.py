from simpy import Environment
from config import MINUTES_PER_TICK, SIMULATION_DAYS, DATE_OF_SIMULATION

from components.battery import Battery
from components.panel import Panel
from components.weather import Weather
from components.inverter import Inverter
from components.grid import Grid
from components.home import Home

from datetime import datetime, timedelta

import math

def Simulate(env: Environment, weather: Weather, panel: Panel, home: Home, inverter: Inverter, battery: Battery, grid: Grid):
    dt = datetime.strptime(DATE_OF_SIMULATION, "%d/%m/%Y")
    print(dt)

    while True:
        current_hour = env.now % 24
        print("----------------------------")
        print(dt)
        
        if current_hour == 0:
            weather.update(dt)
            print(f"Weather update: Weather is {weather.weather}, Cloud coverage is {weather.cloud_coverage}")

        panel.update(weather.cloud_coverage)
        home.update()
        inverter.update(panel.generation, home.totalLoad)
        battery.update()
        grid.update()
        
        dt+=timedelta(minutes=MINUTES_PER_TICK)
        yield env.timeout(MINUTES_PER_TICK / 60)

def main() -> None:
    print()
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