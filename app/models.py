from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import *
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    pv_sytems = relationship("PVSystem", back_population="owner")

class PVSystem(Base):
    __tablename__ = "pv_sytems"
    id = Column(Integer, primary_key=True, index = True)
    user_id = Column(String, ForeignKey("user.id"))
    name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    kwp = Column(Float)
    tilt = Column(Float)
    azimuth = Column(Float)
    owner = relationship("User", back_populates="pv_sytems")

class PVSystemBase():
    name: str
    latitude: float
    longitude: float
    kwp: float
    tilt: float
    azimuth: float

class PVSystemCreate(PVSystemBase):
    pass

class PVSystemRead(PVSystemBase):
    id: int 
    user_id: str

class Device(BaseModel):
    id: str
    device_name: str # eg. "Tesla Model 3 von Matthias"
    type: str  # e.g., "ev", "washer"
    consumption: float  # in kWh

class WeatherData(BaseModel):
    temperature: float
    humidity: float
    wind_speed: float
    cloud_cover: float
    solar_irradiance: Optional[float] = None

class PVData(BaseModel):
    dc_input: float
    output_power: float
    battery_soc: float

class OptimalTimeRequest(BaseModel):
    device: Device
    production: List[float]

class ExcessDurationRequest(BaseModel):
    production: List[float]
    consumption: float
