from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
import os

from .services import ForecastingService
from .database import get_db, Base, engine
from .models import User, PVSystem, PVSystemCreate, PVSystemRead, ForecastRequest, ForecastResponse
from .auth.auth_implementations import get_auth_service, AuthServiceInterface

app = FastAPI()
service = ForecastingService()
security = HTTPBearer()

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not create database tables: {e}")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Get appropriate auth service based on environment
    auth_service = get_auth_service(db)
    current_user = await auth_service.get_current_user(credentials.credentials)
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    return current_user

@app.get("/forecast/hello")
def read_root():
    return {"message": "Hello from Forecasting Tool Microservice"}

@app.get("/health")
def health_check():
    """Health check endpoint for Docker/Kubernetes"""
    return {
        "status": "healthy", 
        "service": "forecasting-ms",
        "version": "1.0.0"
    }

@app.post("/forecast/production/{system_id}")
def forecast_production(
    system_id: int,
    request: ForecastRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if system belongs to user
    pv_system = db.query(PVSystem).filter(
        PVSystem.id == system_id,
        PVSystem.user_id == current_user.id
    ).first()
    
    if not pv_system:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PV System not found")
    
    # Generate forecast
    weather_data = service.get_weather_data(pv_system, days=7)
    power_forecast = service.predict_production(pv_system, weather_data)
    response = service.format_forecast_response(system_id, power_forecast)
    
    return response

@app.post("/systems", response_model=PVSystemRead, status_code=status.HTTP_201_CREATED)
def create_pv_system(
    system: PVSystemCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_system = PVSystem(
        user_id=current_user.id,
        name=system.name,
        latitude=system.latitude,
        longitude=system.longitude,
        kwp=system.kwp,
        tilt=system.tilt,
        azimuth=system.azimuth
    )
    db.add(db_system)
    db.commit()
    db.refresh(db_system)
    return db_system

@app.get("/systems", response_model=List[PVSystemRead])
def get_user_systems(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    systems = db.query(PVSystem).filter(PVSystem.user_id == current_user.id).all()
    return systems
