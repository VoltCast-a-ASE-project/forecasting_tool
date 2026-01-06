import pvlib
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from .models import PVSystem
from .weather_client import OpenMeteoClient

# Date/Time format constants (ISO 8601 compliant)
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # Full ISO 8601 timestamp
DAY_FORMAT = "%Y-%m-%d"                # YYYY-MM-DD format


class ForecastingService:
    """Service for calculating PV power production forecasts based on weather data."""
    
    def __init__(self):
        self.weather_client = OpenMeteoClient()
    
    def create_pv_system_model(self, pv_system: PVSystem) -> pvlib.pvsystem.PVSystem:
        """
        Convert SQLAlchemy PVSystem to pvlib PVSystem model for calculations.
        
        Args:
            pv_system: Database PV system configuration
            
        Returns:
            pvlib.pvsystem.PVSystem: Configured PV system model
        """
        # Convert kWp to W for pvlib (peak DC power)
        pdc0 = pv_system.kwp * 1000  # 5.0 kWp = 5000 W DC
        
        # Standard PV module parameters (can be customized)
        module_parameters = {
            'pdc0': pdc0,                    # Peak DC power at STC (W)
            'gamma_pdc': -0.004,              # Temperature coefficient (%/°C)
        }
        
        # Standard temperature model parameters
        temperature_model_parameters = {
            'a': -3.56,      # a coefficient
            'b': -0.075,     # b coefficient  
            'deltaT': 3       # Temperature difference above ambient (°C)
        }
        
        return pvlib.pvsystem.PVSystem(
            surface_tilt=pv_system.tilt,
            surface_azimuth=pv_system.azimuth,
            module_parameters=module_parameters,
            temperature_model_parameters=temperature_model_parameters
        )
    
    def get_weather_data(self, pv_system: PVSystem, days: int = 2) -> pd.DataFrame:
        """
        Fetch weather forecast data for PV system location.
        
        Args:
            pv_system: PV system with location data
            days: Number of forecast days (1-7)
            
        Returns:
            pd.DataFrame: Weather data with pvlib-compatible columns
        """
        return self.weather_client.get_forecast(
            lat=pv_system.latitude,
            lon=pv_system.longitude,
            days=days
        )
    
    def predict_production(self, pv_system: PVSystem, weather_df: pd.DataFrame) -> pd.Series:
        """
        Calculate AC power production from weather data using pvlib with proper system model.
        
        Args:
            pv_system: PV system configuration
            weather_df: Weather data from OpenMeteo
            
        Returns:
            pd.Series: Hourly AC power production in kilowatts
        """
        if weather_df.empty:
            return pd.Series(dtype=float)
        
        
        # Prepare weather data for pvlib using proper system model
        # Convert temperature to Celsius for pvlib (pvlib handles units internally)
        weather_data = {
            'ghi': weather_df['ghi'],
            'dni': weather_df['dni'], 
            'dhi': weather_df['dhi'],
            'temp_air': weather_df['temp_air'],  # Keep in Celsius
            'wind_speed': weather_df['wind_speed']
        }
        
        # Calculate plane-of-array irradiance using system orientation
        solar_position = pvlib.solarposition.get_solarposition(
            weather_df.index,
            pv_system.latitude,
            pv_system.longitude
        )
        
        poa_irradiance = pvlib.irradiance.get_total_irradiance(
            surface_tilt=pv_system.tilt,
            surface_azimuth=pv_system.azimuth,
            solar_zenith=solar_position['apparent_zenith'],
            solar_azimuth=solar_position['azimuth'],
            dni=weather_df['dni'],
            ghi=weather_df['ghi'],
            dhi=weather_df['dhi']
        )
        
        # Calculate DC power using database system parameters
        dc_power = pvlib.pvsystem.pvwatts_dc(
            g_poa_effective=poa_irradiance['poa_global'],
            temp_cell=weather_data['temp_air'] + 3,
            pdc0=pv_system.kwp * 1000,  # Use database kwp directly
            gamma_pdc=-0.003  # Use standard temperature coefficient
        )
        
        # Convert to AC power with typical inverter efficiency (95%)
        inverter_efficiency = 0.95
        ac_power = dc_power * inverter_efficiency
        
        # Convert to kilowatts and return as Series
        ac_power_kw = pd.Series(ac_power / 1000, index=weather_df.index)
        return ac_power_kw
    
    def calculate_energy_kwh(self, power_series: pd.Series) -> float:
        """
        Calculate total energy in kWh from power series.
        
        Args:
            power_series: Hourly power values in kW
            
        Returns:
            float: Total energy in kWh
        """
        # Energy = Power × Time (1 hour for each data point)
        return power_series.sum()  # Series of kW summed = kWh
    
    def format_forecast_response(self, system_id: int, power_series: pd.Series) -> Dict:
        """
        Format forecasting results into API response format with daily grouping.
        
        Args:
            system_id: PV system identifier
            power_series: Hourly power production in kW
            
        Returns:
            Dict: Formatted forecast response with daily structure
        """
        # Validate power series length (only in production, not in tests)
        if len(power_series) > 168:
            raise ValueError(f"Maximum 168 hours allowed, got {len(power_series)}")
        
        total_energy_kwh = self.calculate_energy_kwh(power_series)
        
        forecast_list = []
         # Always use 00:00 of current day as starting point
        forecast_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day_index in range(7):
            day_start = day_index * 24
            day_end = (day_index + 1) * 24
            
            # Extract hours for this day
            day_hours = power_series.iloc[day_start:day_end]
            
            # Format date string (YYYY-MM-DD)
            day_date = forecast_start + timedelta(days=day_index)
            day_str = day_date.strftime(DAY_FORMAT)
            
            # Calculate daily energy
            daily_energy = sum(float(power) for power in day_hours)
            
            # Create hourly forecasts for this day
            daily_forecasts = []
            for hour, power_kw in enumerate(day_hours):
                # Create timestamp for this hour (ISO 8601)
                timestamp = day_date.replace(hour=hour)
                daily_forecasts.append({
                    'timestamp': timestamp.strftime(DATETIME_FORMAT),
                    'power_kw': round(float(power_kw), 2)
                })
            
            forecast_list.append({
                'day': day_str,
                'daily_energy_kwh': round(daily_energy, 2),
                'forecast': daily_forecasts
            })
        
        return {
            'system_id': system_id,
            'total_energy_kwh': round(total_energy_kwh, 2),
            'forecast_from': forecast_start.strftime(DATETIME_FORMAT),
            'forecast_to': (forecast_start + timedelta(days=7)).strftime(DATETIME_FORMAT),
            'forecast_hours': len(power_series),  # sollte 168 sein
            'forecast_list': forecast_list
        }
