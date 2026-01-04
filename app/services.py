import pvlib
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from .models import PVSystem
from .weather_client import OpenMeteoClient


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
        Calculate AC power production from weather data using pvlib.
        
        Args:
            pv_system: PV system configuration
            weather_df: Weather data from OpenMeteo
            
        Returns:
            pd.Series: Hourly AC power production in kilowatts
        """
        if weather_df.empty:
            return pd.Series(dtype=float)
        
        # Create pvlib system model
        system_model = self.create_pv_system_model(pv_system)
        
        # Prepare weather data for pvlib
        # Convert temperature to Kelvin for pvlib
        weather_data = {
            'ghi': weather_df['ghi'],
            'dni': weather_df['dni'], 
            'dhi': weather_df['dhi'],
            'temp_air': weather_df['temp_air'] + 273.15,  # Celsius to Kelvin
            'wind_speed': weather_df['wind_speed']
        }
        
        # Calculate DC power from weather and PV system configuration
        # Simplified PVWatts model using effective irradiance
        g_poa_effective = weather_data['ghi']  # Simplified - in real implementation would calculate POA
        temp_cell = weather_data['temp_air'] + 3  # Estimate cell temperature
        
        # Get module power at reference conditions (based on kwp rating)
        pdc0 = pv_system.kwp * 1000  # Convert kWp to W
        
        # Temperature coefficient (typical value)
        gamma_pdc = -0.003
        
        dc_power = pvlib.pvsystem.pvwatts_dc(
            g_poa_effective=g_poa_effective,
            temp_cell=temp_cell,
            pdc0=pdc0,
            gamma_pdc=gamma_pdc
        )
        
        # Convert to AC power with typical inverter efficiency (95%)
        inverter_efficiency = 0.95
        ac_power = dc_power * inverter_efficiency
        
        # Convert to kilowatts and return as Series
        ac_power_kw = ac_power / 1000
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
        Format forecasting results into API response format.
        
        Args:
            system_id: PV system identifier
            power_series: Hourly power production in kW
            
        Returns:
            Dict: Formatted forecast response
        """
        total_energy_kwh = self.calculate_energy_kwh(power_series)
        
        forecast_data = []
        for index in power_series.index:
            power_kw = power_series[index]
            # Calculate energy for this hour
            energy_kwh = power_kw  # kW for 1 hour = kWh
            
            forecast_data.append({
                'timestamp': str(index),
                'power_kw': round(power_kw, 2),
                'energy_kwh': round(energy_kwh, 2)
            })
        
        now = datetime.now(timezone.utc)
        return {
            'system_id': system_id,
            'total_energy_kwh': round(total_energy_kwh, 2),
            'forecast_from': now,
            'forecast_to': now + timedelta(days=7),
            'forecast_hours': len(power_series),
            'forecast': forecast_data
        }
        
        now = datetime.now(timezone.utc)
        return {
            'system_id': system_id,
            'total_energy_kwh': round(total_energy_kwh, 2),
            'forecast_from': now,
            'forecast_to': now + timedelta(days=7),
            'forecast_hours': len(power_series),
            'forecast': forecast_data
        }