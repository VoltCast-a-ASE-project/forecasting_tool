import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Forecasting Tool Microservice"}

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
    device_data = {"id": "1", "type": "ev", "consumption": 10.0}
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
    device_data = {"id": "1", "type": "ev", "consumption": 10.0}
    response = client.post("/devices/add", json=device_data)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["device"]["id"] == "1"