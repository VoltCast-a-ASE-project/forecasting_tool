from pydantic import BaseModel
from typing import Optional, List

class Device(BaseModel):
    id: str
    type: str  # e.g., "ev", "washer"
    consumption: float  # in kWh

class WeatherData(BaseModel):
    temperature: float
    humidity: float
    wind_speed: float
    cloud_cover: float
    solar_irradiance: Optional[float] = None

class PVData(BaseModel):
    dc_input: float
    output_power: float
    battery_soc: float

class OptimalTimeRequest(BaseModel):
    device: Device
    production: List[float]

class ExcessDurationRequest(BaseModel):
    production: List[float]
    consumption: float