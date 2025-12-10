import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import ForecastingService
from app.models import WeatherData, Device

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Forecasting Tool Microservice"}

def test_hello_frontend():
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from the Forecasting Tool Microservice"}

def test_forecast_production():
    weather_data = {
        "temperature": 25.0,
        "humidity": 60.0,
        "wind_speed": 5.0,
        "cloud_cover": 20.0
    }
    response = client.post("/forecast/production", json=weather_data, params={"days": 1})
    assert response.status_code == 200
    data = response.json()
    assert "production" in data
    assert len(data["production"]) == 1

def test_optimal_time():
    device_data = {"id": "1", "device_name": "Tesla", "type": "ev", "consumption": 10.0}
    production = [100.0]
    response = client.post("/forecast/optimal-time", json={"device": device_data, "production": production})
    assert response.status_code == 200
    data = response.json()
    assert "optimal_time" in data

def test_excess_duration():
    production = [100.0, 120.0]
    consumption = 50.0
    response = client.post("/forecast/excess", json={"production": production, "consumption": consumption})
    assert response.status_code == 200
    data = response.json()
    assert "duration" in data

def test_add_device():
    device_data = {"id": "1", "device_name": "Tesla", "type": "ev", "consumption": 10.0}
    response = client.post("/devices/add", json=device_data)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["device"]["id"] == "1"


# Unit tests for ForecastingService

def test_predict_production():
    service = ForecastingService()
    weather = WeatherData(temperature=25.0, humidity=60.0, wind_speed=5.0, cloud_cover=20.0, solar_irradiance=800.0)
    result = service.predict_production(weather, days=1)
    assert "production" in result
    assert len(result["production"]) == 1
    assert isinstance(result["production"][0], float)
    assert result["production"][0] > 0  # Basic check for positive production

def test_predict_production_without_irradiance():
    service = ForecastingService()
    weather = WeatherData(temperature=25.0, humidity=60.0, wind_speed=5.0, cloud_cover=20.0)
    result = service.predict_production(weather, days=2)
    assert len(result["production"]) == 2
    assert all(p > 0 for p in result["production"])

def test_optimal_time_for_device():
    service = ForecastingService()
    device = Device(id="1", device_name="Tesla", type="ev", consumption=10.0)
    production = [50.0, 100.0, 80.0]
    result = service.optimal_time_for_device(device, production)
    assert isinstance(result, str)
    assert ":" in result  # Should be in HH:MM format

def test_excess_power_duration():
    service = ForecastingService()
    production = [100.0, 120.0, 80.0]
    consumption = 90.0
    result = service.excess_power_duration(production, consumption)
    assert isinstance(result, float)
    assert result == 2.0  # 100 and 120 > 90
