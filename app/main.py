from fastapi import FastAPI
from .services import ForecastingService

app = FastAPI()
service = ForecastingService()

@app.get("/")
def read_root():
    return {"message": "Hello from the Forecasting Tool Microservice"}

@app.post("/forecast/production")
def forecast_productionw():
    pass

#@app.post("/devices/add")
#def add_device(device: Device):
#    # Placeholder: Add to DB
#    return {"message": "Device added", "device": device}
