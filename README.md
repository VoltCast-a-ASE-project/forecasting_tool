# Forecasting Tool Microservice

A Python-based microservice for forecasting PV production and optimizing device usage times using physics-based simulations.

## Features

- **Physics-Based Forecasting**: Uses `pvlib` to simulate PV panel performance based on:
  - Location (Latitude/Longitude)
  - Panel configuration (Tilt, Azimuth, Capacity kWp)
  - Temperature effects on efficiency
- **Optimization**: Calculates the best time window to run high-consumption devices (EVs, Washing Machines) based on excess solar power.
- **Weather Integration**: Automatically fetches high-precision solar irradiance (GHI, DNI) and weather data from OpenMeteo API.

## API Endpoints

### 1. Forecast Production
`POST /forecast/production`
Returns the estimated power generation (kW) for the next N days.
- **Input**: `PVSystemConfig` (Location, Tilt, kWp)
- **Output**: Time series of power output.

### 2. Optimal Time
`POST /forecast/optimal-time`
Finds the best start time for a device to maximize solar self-consumption.
- **Input**: Device specs (Power rating, energy needed), System Config.
- **Output**: Recommended start/end time, solar coverage %.

## Development

### Prerequisites
- Python 3.10+
- `pvlib`, `fastapi`, `uvicorn`, `requests`, `pandas`

### Setup
```bash
# Create venv
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running
```bash
# Start server with auto-reload
uvicorn app.main:app --reload --port 8084
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_main.py -v
```

## Architecture

lorem ipsum
