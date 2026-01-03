import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from app.services import ForecastingService
from app.models import PVSystem


class TestForecastingService:
    """Test suite for ForecastingService class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a new instance with mocked weather client
        self.service = ForecastingService()
        
        # Sample PV system for testing
        self.sample_pv_system = PVSystem(
            id=1,
            user_id="test-user",
            name="Test PV System",
            latitude=48.2082,  # Vienna
            longitude=16.3738,
            kwp=5.0,  # 5 kW peak
            tilt=35.0,  # Typical roof tilt
            azimuth=180.0  # South-facing
        )

    def test_create_pv_system_model(self):
        """Test creation of pvlib PV system model from database model."""
        pv_system_model = self.service.create_pv_system_model(self.sample_pv_system)
        
        # Check that pvlib system was created correctly
        # pvlib.pvsystem.PVSystem stores mount info in arrays[0].mount
        assert hasattr(pv_system_model.arrays[0].mount, 'surface_tilt')
        assert hasattr(pv_system_model.arrays[0].mount, 'surface_azimuth')
        assert hasattr(pv_system_model.arrays[0], 'module_parameters')
        assert pv_system_model is not None

    def test_get_weather_data_success(self):
        """Test successful weather data fetching."""
        # Mock successful weather response
        mock_weather_data = pd.DataFrame({
            'temp_air': [15.0, 16.0],
            'ghi': [400.0, 450.0],
            'dni': [350.0, 400.0],
            'dhi': [50.0, 50.0],
            'wind_speed': [3.0, 3.5]
        }, index=pd.to_datetime(['2024-01-01 10:00:00', '2024-01-01 11:00:00']))
        
        with patch.object(self.service.weather_client, 'get_forecast', return_value=mock_weather_data):
            result = self.service.get_weather_data(self.sample_pv_system, days=2)
            
        assert not result.empty
        assert len(result) == 2
        assert result.iloc[0]['ghi'] == 400.0

    def test_get_weather_data_empty(self):
        """Test handling of empty weather data response."""
        empty_weather_data = pd.DataFrame()
        
        with patch.object(self.service.weather_client, 'get_forecast', return_value=empty_weather_data):
            result = self.service.get_weather_data(self.sample_pv_system, days=2)
            
        assert result.empty

    def test_predict_production_success(self):
        """Test successful power production prediction."""
        # Create mock weather data
        weather_data = pd.DataFrame({
            'temp_air': [15.0],
            'ghi': [400.0],
            'dni': [350.0],
            'dhi': [50.0],
            'wind_speed': [3.0]
        }, index=pd.to_datetime(['2024-01-01 10:00:00']))
        
        result = self.service.predict_production(self.sample_pv_system, weather_data)
        
        assert not result.empty
        assert result.iloc[0] > 0  # Power should be positive

    def test_predict_production_empty_weather(self):
        """Test production prediction with empty weather data."""
        empty_weather_data = pd.DataFrame()
        
        result = self.service.predict_production(self.sample_pv_system, empty_weather_data)
        
        assert result.empty

    def test_calculate_energy_kwh(self):
        """Test energy calculation from power series."""
        # Sample power data (kW for each hour)
        power_data = pd.Series([1.0, 2.0, 1.5, 0.5])
        
        total_energy = self.service.calculate_energy_kwh(power_data)
        
        expected_energy = 1.0 + 2.0 + 1.5 + 0.5  # = 5.0 kWh
        assert total_energy == expected_energy

    def test_calculate_energy_kwh_empty(self):
        """Test energy calculation with empty power series."""
        empty_power_data = pd.Series(dtype=float)
        
        total_energy = self.service.calculate_energy_kwh(empty_power_data)
        
        assert total_energy == 0.0

    def test_format_forecast_response(self):
        """Test formatting of forecast response."""
        # Sample power series
        timestamps = pd.to_datetime(['2024-01-01 10:00:00', '2024-01-01 11:00:00'])
        power_series = pd.Series([1.5, 2.0], index=timestamps)
        
        response = self.service.format_forecast_response(system_id=123, power_series=power_series)
        
        assert response['system_id'] == 123
        assert len(response['forecast']) == 2
        assert response['forecast'][0]['power_kw'] == 1.5
        assert response['forecast'][0]['energy_kwh'] == 1.5
        assert response['total_energy_kwh'] == 3.5

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
        
        # Mock the weather client method directly
        with patch.object(self.service.weather_client, 'get_forecast', return_value=mock_weather_data) as mock_get_forecast:
            # Test complete flow
            weather_data = self.service.get_weather_data(self.sample_pv_system, days=2)
            power_forecast = self.service.predict_production(self.sample_pv_system, weather_data)
            response = self.service.format_forecast_response(system_id=123, power_series=power_forecast)
            
            # Verify integration worked
            mock_get_forecast.assert_called_once_with(
                lat=48.2082, 
                lon=16.3738, 
                days=2
            )
            
            assert response['system_id'] == 123
            assert len(response['forecast']) == 3
            assert response['total_energy_kwh'] > 0