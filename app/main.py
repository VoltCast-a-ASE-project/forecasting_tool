from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
import os

from .services import ForecastingService
from .database import get_db
from .models import User, PVSystem, PVSystemCreate, PVSystemRead
from .auth.auth_implementations import get_auth_service, AuthServiceInterface

app = FastAPI()
service = ForecastingService()
security = HTTPBearer()

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

@app.get("/")
def read_root():
    return {"message": "Hello from Forecasting Tool Microservice"}

@app.post("/forecast/production")
def forecast_production():
    pass

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