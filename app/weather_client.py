import requests
import pandas as pd
from datetime import datetime

class OpenMeteoClient:
    """
    A client to fetch weather forecast data from the OpenMeteo API.
    Returns data in a pandas DataFrame compatible with pvlib.
    """
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def get_forecast(self, lat: float, lon: float, days: int = 2) -> pd.DataFrame:
        """
        Fetches hourly weather forecast for a given location.

        Args:
            lat (float): Latitude of the location.
            lon (float): Longitude of the location.
            days (int): Number of forecast days (max 7).

        Returns:
            pd.DataFrame: A DataFrame with a DatetimeIndex and columns:
                          'temp_air', 'ghi', 'dni', 'dhi', 'wind_speed'.
                          Returns an empty DataFrame on error.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,shortwave_radiation,direct_normal_irradiance,diffuse_radiation,wind_speed_10m",
            "forecast_days": days,
            "timezone": "auto"
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            data = response.json()

            hourly = data.get("hourly", {})
            
            # Check if we got any data
            if not hourly.get("time"):
                print("Warning: No time data received from OpenMeteo API.")
                return pd.DataFrame()

            df = pd.DataFrame({
                "temp_air": hourly.get("temperature_2m"),
                "ghi": hourly.get("shortwave_radiation"),
                "dni": hourly.get("direct_normal_irradiance"),
                "dhi": hourly.get("diffuse_radiation"),
                "wind_speed": hourly.get("wind_speed_10m")
            })

            df.index = pd.to_datetime(hourly.get("time"))
            return df

        except requests.RequestException as e:
            print(f"Error fetching weather data from OpenMeteo: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return pd.DataFrame()
