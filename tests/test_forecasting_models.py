import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from app.models import ForecastRequest, HourlyForecast, DayForecast, ForecastResponse


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
        """Test that ForecastResponse accepts valid data with daily structure."""
        now = datetime.now(timezone.utc)
        hourly_forecasts = [
            HourlyForecast(
                timestamp="2024-01-15T10:00:00Z",
                power_kw=4.5
            ),
            HourlyForecast(
                timestamp="2024-01-15T11:00:00Z",
                power_kw=5.2
            )
        ]
        
        daily_forecasts = [
            DayForecast(
                day="2024-01-15T",
                daily_energy_kwh=9.7,
                forecast=hourly_forecasts
            )
        ]

        response = ForecastResponse(
            system_id=123,
            total_energy_kwh=9.7,
            forecast_from=now,
            forecast_to=now + timedelta(days=7),
            forecast_hours=48,
            forecast_list=daily_forecasts
        )
        
        assert response.system_id == 123
        assert response.total_energy_kwh == 9.7
        assert len(response.forecast_list) == 1
        assert len(response.forecast_list[0].forecast) == 2
        assert response.forecast_list[0].forecast[0].power_kw == 4.5
        assert response.forecast_list[0].forecast[1].power_kw == 5.2

    def test_forecast_response_empty_forecast(self):
        """Test that ForecastResponse accepts empty forecast list."""
        now = datetime.now(timezone.utc)
        response = ForecastResponse(
            system_id=123,
            total_energy_kwh=0.0,
            forecast_from=now,
            forecast_to=now + timedelta(days=7),
            forecast_hours=0,
            forecast_list=[]
        )
        
        assert response.system_id == 123
        assert response.total_energy_kwh == 0.0
        assert len(response.forecast_list) == 0

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
                forecast_list=[]
            )

        assert "input should be greater than or equal to 0" in str(exc_info.value).lower()

    def test_hourly_forecast_valid_timestamp(self):
        """Test that HourlyForecast accepts valid timestamp."""
        forecast = HourlyForecast(
            timestamp="2024-01-15T10:00:00Z",
            power_kw=4.5
        )
        
        assert forecast.timestamp == "2024-01-15T10:00:00Z"
        assert forecast.power_kw == 4.5

    def test_hourly_forecast_negative_power(self):
        """Test that HourlyForecast rejects negative power."""
        with pytest.raises(ValidationError) as exc_info:
            HourlyForecast(
                timestamp="2024-01-15T10:00:00Z",
                power_kw=-1.0
            )

        assert "input should be greater than or equal to 0" in str(exc_info.value).lower()

    def test_day_forecast_structure(self):
        """Test that DayForecast accepts valid hourly forecast list."""
        hourly_forecasts = [
            HourlyForecast(timestamp="2024-01-15T10:00:00Z", power_kw=4.5),
            HourlyForecast(timestamp="2024-01-15T11:00:00Z", power_kw=5.2)
        ]
        
        day_forecast = DayForecast(
            day="2024-01-15T",
            daily_energy_kwh=9.7,
            forecast=hourly_forecasts
        )
        
        assert day_forecast.day == "2024-01-15T"
        assert len(day_forecast.forecast) == 2
        assert day_forecast.forecast[0].power_kw == 4.5
        assert day_forecast.forecast[1].power_kw == 5.2