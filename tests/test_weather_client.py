import pytest
from unittest.mock import patch, Mock
import pandas as pd
import requests
from app.weather_client import OpenMeteoClient

# --- Test Cases ---

def test_client_initialization():
    """Test that the client can be initialized."""
    client = OpenMeteoClient()
    assert client.BASE_URL == "https://api.open-meteo.com/v1/forecast"

@patch('app.weather_client.requests.get')
def test_get_forecast_success(mock_get):
    """Test a successful API call and data parsing."""
    # 1. Arrange: Setup the mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hourly": {
            "time": ["2023-10-27T10:00", "2023-10-27T11:00"],
            "temperature_2m": [15.0, 16.5],
            "shortwave_radiation": [200.0, 350.0],
            "direct_normal_irradiance": [400.0, 600.0],
            "diffuse_radiation": [50.0, 80.0],
            "wind_speed_10m": [5.0, 6.0]
        }
    }
    mock_get.return_value = mock_response

    # 2. Act: Call the method under test
    client = OpenMeteoClient()
    df = client.get_forecast(lat=52.52, lon=13.41, days=1)

    # 3. Assert: Check the results
    assert not df.empty
    assert len(df) == 2
    assert isinstance(df.index, pd.DatetimeIndex)
    assert "temp_air" in df.columns
    assert "ghi" in df.columns
    assert "dni" in df.columns
    assert "dhi" in df.columns
    assert "wind_speed" in df.columns
    
    # Check specific data points
    assert df.iloc[0]["temp_air"] == 15.0
    assert df.iloc[1]["ghi"] == 350.0

@patch('app.weather_client.requests.get')
def test_get_forecast_api_error(mock_get):
    """Test handling of API errors (e.g., 404, 500)."""
    # 1. Arrange: Simulate a 404 error
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
    mock_get.return_value = mock_response

    # 2. Act
    client = OpenMeteoClient()
    df = client.get_forecast(lat=52.52, lon=13.41)

    # 3. Assert
    assert df.empty

@patch('app.weather_client.requests.get')
def test_get_forecast_network_error(mock_get):
    """Test handling of network errors (e.g., timeout)."""
    # 1. Arrange: Simulate a connection timeout
    mock_get.side_effect = requests.exceptions.RequestException("Connection timed out")

    # 2. Act
    client = OpenMeteoClient()
    df = client.get_forecast(lat=52.52, lon=13.41)

    # 3. Assert
    assert df.empty

@patch('app.weather_client.requests.get')
def test_get_forecast_empty_data(mock_get):
    """Test handling of a successful response with no hourly data."""
    # 1. Arrange: Simulate a response with empty 'hourly' object
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"hourly": {}}
    mock_get.return_value = mock_response

    # 2. Act
    client = OpenMeteoClient()
    df = client.get_forecast(lat=52.52, lon=13.41)

    # 3. Assert
    assert df.empty