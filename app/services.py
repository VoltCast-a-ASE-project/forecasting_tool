import pvlib
import pandas as pd
from .models import WeatherData, PVData, Device

class ForecastingService:
    def __init__(self):
        # Simplified PV system without SAM for now
        self.location = pvlib.location.Location(latitude=48.0, longitude=16.0)  # Vienna as example

    def predict_production(self, weather: WeatherData, days: int) -> dict:
        # Simplified prediction: Base on irradiance and temperature
        base_production = (weather.solar_irradiance or 800) * 0.15 * (1 - (weather.temperature - 25) * 0.005)
        production = [base_production] * days  # kWh per day
        return {"production": production}

    def optimal_time_for_device(self, device: Device, production: list) -> str:
        # Find time with max production for charging
        max_index = production.index(max(production))
        hour = (max_index % 24) + 6  # Assume start at 6 AM
        return f"{hour:02d}:00"

    def excess_power_duration(self, production: list, consumption: float) -> float:
        # Calculate hours where production > consumption
        excess_hours = sum(1 for p in production if p > consumption)
        return excess_hours