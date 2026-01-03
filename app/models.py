from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    pv_systems = relationship("PVSystem", back_populates="user")

class PVSystem(Base):
    __tablename__ = "pv_systems"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    kwp = Column(Float)
    tilt = Column(Float)
    azimuth = Column(Float)
    user = relationship("User", back_populates="pv_systems")

class PVSystemBase(BaseModel):
    name: str
    latitude: float = Field(
        ge=-90, le=90, 
        description="Latitude must be between -90° (South Pole) and 90° (North Pole). Positive values = Northern Hemisphere, Negative values = Southern Hemisphere"
    )
    longitude: float = Field(
        ge=-180, le=180, 
        description="Longitude must be between -180° and 180°. Positive values = Eastern Hemisphere, Negative values = Western Hemisphere"
    )
    kwp: float = Field(gt=0, description="kWp must be greater than 0")
    tilt: float = Field(ge=0, le=90, description="Tilt angle must be between 0 and 90 degrees")
    azimuth: float = Field(ge=0, lt=360, description="Azimuth must be between 0 and 360 degrees")

class PVSystemCreate(PVSystemBase):
    pass

class PVSystemRead(PVSystemBase):
    id: int 
    user_id: str

    class Config:
        from_attributes = True

class WeatherData(BaseModel):
    temperature: float
    humidity: float
    wind_speed: float
    cloud_cover: float
    solar_irradiance: Optional[float] = None

class ForecastRequest(BaseModel):
    days: int = Field(ge=1, le=7, default=2, description="Days to forecast (1-7)")

class ProductionForecast(BaseModel):
    timestamp: datetime
    power_kw: float = Field(ge=0, description="AC power output in kilowatts")
    energy_kwh: Optional[float] = Field(default=None, ge=0, description="Energy produced in this hour in kWh")

class ForecastResponse(BaseModel):
    system_id: int
    total_energy_kwh: float = Field(ge=0, description="Total energy production in kWh")
    forecast: List[ProductionForecast]

class PVData(BaseModel):
    dc_input: float
    output_power: float
    battery_soc: float