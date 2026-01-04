import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from app.models import ForecastRequest, ProductionForecast, ForecastResponse


class TestForecastingModels:
    """Test suite for Pydantic models related to forecasting."""

    def test_forecast_request_valid_days_in_range(self):
        """Test that ForecastRequest accepts valid days values."""
        # Test minimum value
        request = ForecastRequest(days=1)
        assert request.days == 1

        # Test maximum value
        request = ForecastRequest(days=7)
        assert request.days == 7

        # Test default value (should be 7)
        request = ForecastRequest()
        assert request.days == 7

    def test_forecast_request_invalid_days_below_minimum(self):
        """Test that ForecastRequest rejects days < 1."""
        with pytest.raises(ValidationError) as exc_info:
            ForecastRequest(days=0)

        assert "input should be greater than or equal to 1" in str(exc_info.value).lower()

    def test_forecast_request_invalid_days_above_maximum(self):
        """Test that ForecastRequest rejects days > 7."""
        with pytest.raises(ValidationError) as exc_info:
            ForecastRequest(days=8)

        assert "input should be less than or equal to 7" in str(exc_info.value).lower()

    def test_forecast_response_valid_data(self):
        """Test that ForecastResponse accepts valid data."""
        now = datetime.now(timezone.utc)
        forecast_data = [
            ProductionForecast(
                timestamp=datetime(2024, 1, 15, 10, 0, 0),
                power_kw=4.5,
                energy_kwh=4.5
            ),
            ProductionForecast(
                timestamp=datetime(2024, 1, 15, 11, 0, 0),
                power_kw=5.2,
                energy_kwh=5.2
            )
        ]

        response = ForecastResponse(
            system_id=123,
            total_energy_kwh=9.7,
            forecast_from=now,
            forecast_to=now + timedelta(days=7),
            forecast_hours=168,
            forecast=forecast_data
        )
        
        assert response.system_id == 123
        assert response.total_energy_kwh == 9.7
        assert len(response.forecast) == 2
        assert response.forecast[0].power_kw == 4.5
        assert response.forecast[1].power_kw == 5.2

    def test_forecast_response_empty_forecast(self):
        """Test that ForecastResponse accepts empty forecast list."""
        now = datetime.now(timezone.utc)
        response = ForecastResponse(
            system_id=123,
            total_energy_kwh=0.0,
            forecast_from=now,
            forecast_to=now + timedelta(days=7),
            forecast_hours=0,
            forecast=[]
        )
        
        assert response.system_id == 123
        assert response.total_energy_kwh == 0.0
        assert len(response.forecast) == 0

    def test_forecast_response_negative_total_energy(self):
        """Test that ForecastResponse rejects negative total energy."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError) as exc_info:
            ForecastResponse(
                system_id=123,
                total_energy_kwh=-1.0,
                forecast_from=now,
                forecast_to=now + timedelta(days=7),
                forecast_hours=168,
                forecast=[]
            )

        assert "input should be greater than or equal to 0" in str(exc_info.value).lower()

    def test_production_forecast_valid_timestamp(self):
        """Test that ProductionForecast accepts valid timestamp."""
        forecast = ProductionForecast(
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            power_kw=4.5,
            energy_kwh=4.5
        )
        
        assert forecast.timestamp == datetime(2024, 1, 15, 10, 0, 0)
        assert forecast.power_kw == 4.5
        assert forecast.energy_kwh == 4.5

    def test_production_forecast_negative_power(self):
        """Test that ProductionForecast rejects negative power."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionForecast(
                timestamp=datetime(2024, 1, 15, 10, 0, 0),
                power_kw=-1.0,
                energy_kwh=4.5
            )

        assert "input should be greater than or equal to 0" in str(exc_info.value).lower()

    def test_production_forecast_negative_energy(self):
        """Test that ProductionForecast rejects negative energy."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionForecast(
                timestamp=datetime(2024, 1, 15, 10, 0, 0),
                power_kw=4.5,
                energy_kwh=-1.0
            )

        assert "input should be greater than or equal to 0" in str(exc_info.value).lower()