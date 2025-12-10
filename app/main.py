from fastapi import FastAPI
from .models import Device, WeatherData, OptimalTimeRequest, ExcessDurationRequest
from .services import ForecastingService

app = FastAPI()
service = ForecastingService()

@app.get("/")
def read_root():
    return {"message": "Hello from the Forecasting Tool Microservice"}

@app.post("/forecast/production")
def forecast_production(weather: WeatherData, days: int = 1):
    return service.predict_production(weather, days)

@app.post("/forecast/optimal-time")
def optimal_time(request: OptimalTimeRequest):
    return {"optimal_time": service.optimal_time_for_device(request.device, request.production)}

@app.post("/forecast/excess")
def excess_duration(request: ExcessDurationRequest):
    return {"duration": service.excess_power_duration(request.production, request.consumption)}

@app.post("/devices/add")
def add_device(device: Device):
    # Placeholder: Add to DB
    return {"message": "Device added", "device": device}
