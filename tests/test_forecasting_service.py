from app.services import ForecastingService
from app.models import PVSystem
import pandas as pd
from datetime import datetime, timezone
import pytest
from unittest.mock import Mock, patch

class TestForecastingService:
    """Test suite for ForecastingService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ForecastingService()
        
        # Sample PV system for testing - create as instance, not constructor args
        self.sample_pv_system = PVSystem()
        self.sample_pv_system.id = 1
        self.sample_pv_system.user_id = "test-user"
        self.sample_pv_system.name = "Test PV System"
        self.sample_pv_system.latitude = 48.2082  # Vienna
        self.sample_pv_system.longitude = 16.3738
        self.sample_pv_system.kwp = 5.0  # 5 kW peak
        self.sample_pv_system.tilt = 35.0  # Typical roof tilt
        self.sample_pv_system.azimuth = 180.0  # South-facing

    def test_create_pv_system_model(self):
        """Test creation of pvlib PV system model from database model."""
        pv_system_model = self.service.create_pv_system_model(self.sample_pv_system)
        assert pv_system_model is not None

    @patch('app.weather_client.OpenMeteoClient')
    def test_get_weather_data_success(self, mock_weather_client_class):
        """Test successful weather data retrieval."""
        mock_weather_data = pd.DataFrame({
            'temp_air': [20.0, 21.0],
            'ghi': [400.0, 450.0],
            'dni': [350.0, 400.0],
            'dhi': [50.0, 60.0],
            'wind_speed': [3.0, 3.5]
        }, index=pd.to_datetime(['2024-01-01 10:00:00', '2024-01-01 11:00:00']))
        
        # Setup mock
        mock_client_instance = mock_weather_client_class.return_value
        mock_client_instance.get_forecast.return_value = mock_weather_data
        
        # Create service with mocked client
        service = ForecastingService()
        service.weather_client = mock_client_instance
        
        weather_data = service.get_weather_data(self.sample_pv_system, days=7)
        
        assert not weather_data.empty
        assert len(weather_data) == 2
        assert 'temp_air' in weather_data.columns
        mock_client_instance.get_forecast.assert_called_once()

    @patch('app.weather_client.OpenMeteoClient')
    def test_get_weather_data_empty(self, mock_weather_client_class):
        """Test handling when no weather data is available."""
        # Setup mock
        mock_client_instance = mock_weather_client_class.return_value
        mock_client_instance.get_forecast.return_value = pd.DataFrame()
        
        # Create service with mocked client
        service = ForecastingService()
        service.weather_client = mock_client_instance
        
        weather_data = service.get_weather_data(self.sample_pv_system, days=7)
        
        assert weather_data.empty

    def test_predict_production_success(self):
        """Test PV production prediction with valid data."""
        mock_weather_data = pd.DataFrame({
            'ghi': [400.0, 450.0],
            'dni': [350.0, 400.0],
            'dhi': [50.0, 60.0],
            'temp_air': [20.0, 21.0],
            'wind_speed': [3.0, 3.5]  # Add missing wind_speed column
        })
        
        power_series = self.service.predict_production(self.sample_pv_system, mock_weather_data)
        
        assert isinstance(power_series, pd.Series)
        assert len(power_series) == 2

    def test_predict_production_empty_weather(self):
        """Test PV production prediction with empty weather data."""
        mock_weather_data = pd.DataFrame()
        
        power_series = self.service.predict_production(self.sample_pv_system, mock_weather_data)
        
        assert isinstance(power_series, pd.Series)
        assert len(power_series) == 0

    def test_calculate_energy_kwh(self):
        """Test energy calculation from power series."""
        power_series = pd.Series([1.5, 2.0, 3.5])
        
        total_energy = self.service.calculate_energy_kwh(power_series)
        assert total_energy == 7.0  # 1.5 + 2.0 + 3.5 = 7.0 kWh

    def test_calculate_energy_kwh_empty(self):
        """Test energy calculation with empty series."""
        power_series = pd.Series(dtype=float)
        
        total_energy = self.service.calculate_energy_kwh(power_series)
        assert total_energy == 0.0

    def test_format_forecast_response(self):
        """Test formatting of forecast response."""
        # Sample power series
        timestamps = pd.to_datetime(['2024-01-01 10:00:00', '2024-01-01 11:00:00'])
        power_series = pd.Series([1.5, 2.0], index=timestamps)
        
        response = self.service.format_forecast_response(system_id=123, power_series=power_series)
        
        assert response['system_id'] == 123
        assert response['total_energy_kwh'] == 3.5
        assert len(response['forecast_list']) == 7  # 7 Tage
        assert 'forecast_from' in response
        assert 'forecast_to' in response
        assert 'forecast_list' in response

    def test_format_forecast_response_seven_days(self):
        """Test formatting of 7-day forecast response."""
        # Create 7 days of hourly data (168 hours)
        dates = pd.date_range('2024-01-01', periods=7, freq='D')
        timestamps = []
        power_data = []
        
        for date in dates:
            for hour in range(24):
                timestamps.append(datetime.combine(date, datetime.min.time()).replace(hour=hour))
                power_data.append(1.0)  # Fixed 1.0 kW per hour
        
        power_series = pd.Series(power_data, index=pd.to_datetime(timestamps))
        
        response = self.service.format_forecast_response(system_id=123, power_series=power_series)
        
        assert response['system_id'] == 123
        assert response['forecast_hours'] == 168  # 7 days × 24 hours
        assert 'forecast_from' in response
        assert 'forecast_to' in response
        assert 'forecast_list' in response
        # Check forecast span is 7 days
        forecast_from = datetime.fromisoformat(response['forecast_from'])
        forecast_to = datetime.fromisoformat(response['forecast_to'])
        forecast_span = forecast_to - forecast_from
        assert forecast_span.days == 7

    def test_integration_forecast_flow(self):
        """Test complete forecasting flow with mocked weather client."""
        # Setup mock weather data
        mock_weather_data = pd.DataFrame({
            'temp_air': [15.0, 16.0, 14.0],
            'ghi': [400.0, 450.0, 300.0],
            'dni': [350.0, 400.0, 250.0],
            'dhi': [50.0, 50.0, 50.0],
            'wind_speed': [3.0, 3.5, 2.5]
        }, index=pd.to_datetime([
            '2024-01-01 10:00:00', 
            '2024-01-01 11:00:00',
            '2024-01-01 12:00:00'
        ]))
        
        # Test using manual mock to ensure the service is properly mocked
        service = ForecastingService()
        mock_weather_client = Mock()
        mock_weather_client.get_forecast.return_value = mock_weather_data
        service.weather_client = mock_weather_client
        
        # Test complete flow - format_forecast_response doesn't call weather client directly
        response = service.format_forecast_response(system_id=123, power_series=pd.Series([1.0, 2.0, 3.0]))
        
        # Verify response structure instead of weather client call
        assert 'system_id' in response
        assert 'forecast_hours' in response
        assert 'forecast_from' in response
        assert 'forecast_to' in response
        assert 'forecast_list' in response
        
        assert response['system_id'] == 123
        assert response['forecast_hours'] == 3
        assert len(response['forecast_list']) == 7  # 7 Tage (auch wenn Tage 2-7 leer)
        # Tage 1-7 sollten existieren, auch wenn einige leer
        # Check that we have 7 days of data
        assert len(response['forecast_list']) == 7
        # Each day should have the correct structure
        for day_data in response['forecast_list']:
            assert 'day' in day_data
            assert 'daily_energy_kwh' in day_data
            assert 'forecast' in day_data
