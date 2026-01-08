import pytest
import asyncio
import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models import User


# Set environment variables for testing
os.environ["TESTING"] = "false"  # Use real JWT auth for integration tests
os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["ALGORITHM"] = "HS256"

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_integration.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def valid_jwt_token():
    """Create a valid JWT token for authentication"""
    payload = {
        "sub": "test@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, "test-secret-key", "HS256")


@pytest.fixture
def expired_jwt_token():
    """Create an expired JWT token"""
    payload = {
        "sub": "test@example.com",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2)
    }
    return jwt.encode(payload, "test-secret-key", "HS256")


@pytest.fixture
def invalid_jwt_token():
    """Create an invalid JWT token"""
    return "this.is.not.a.valid.jwt"


class TestAuthenticationIntegration:
    """Integration tests for authentication"""
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token returns 401"""
        response = client.get("/forecast/systems")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
    
    def test_protected_endpoint_with_expired_token(self, client, expired_jwt_token):
        """Test accessing protected endpoint with expired token returns 401"""
        headers = {"Authorization": f"Bearer {expired_jwt_token}"}
        response = client.get("/forecast/systems", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]
    
    def test_protected_endpoint_with_invalid_token(self, client, invalid_jwt_token):
        """Test accessing protected endpoint with invalid token returns 401"""
        headers = {"Authorization": f"Bearer {invalid_jwt_token}"}
        response = client.get("/forecast/systems", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]
    
    def test_protected_endpoint_with_valid_token(self, client, valid_jwt_token):
        """Test accessing protected endpoint with valid token returns 200"""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        response = client.get("/forecast/systems", headers=headers)
        assert response.status_code == 200
        assert response.json() == []  # Empty list for new user
    
    def test_create_system_with_valid_token(self, client, valid_jwt_token):
        """Test creating a PV system with valid authentication"""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        system_data = {
            "name": "Test System",
            "latitude": 48.2082,
            "longitude": 16.3738,
            "kwp": 8.5,
            "tilt": 35.0,
            "azimuth": 180.0
        }
        
        response = client.post("/forecast/systems", json=system_data, headers=headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == "Test System"
        assert data["latitude"] == 48.2082
        assert data["longitude"] == 16.3738
        assert data["kwp"] == 8.5
        assert data["tilt"] == 35.0
        assert data["azimuth"] == 180.0
        assert "user_id" in data
        assert "id" in data
    
    def test_create_system_without_token(self, client):
        """Test creating a PV system without authentication returns 401"""
        system_data = {
            "name": "Test System",
            "latitude": 48.2082,
            "longitude": 16.3738,
            "kwp": 8.5,
            "tilt": 35.0,
            "azimuth": 180.0
        }
        
        response = client.post("/forecast/systems", json=system_data)
        assert response.status_code == 401
    
    def test_user_isolation_different_tokens(self, client):
        """Test that different users cannot access each other's systems"""
        # Create token for user1
        user1_payload = {
            "sub": "user1@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc)
        }
        user1_token = jwt.encode(user1_payload, "test-secret-key", "HS256")
        
        # Create token for user2
        user2_payload = {
            "sub": "user2@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc)
        }
        user2_token = jwt.encode(user2_payload, "test-secret-key", "HS256")
        
        # User1 creates a system
        headers1 = {"Authorization": f"Bearer {user1_token}"}
        system_data = {
            "name": "User1 System",
            "latitude": 48.2082,
            "longitude": 16.3738,
            "kwp": 8.5,
            "tilt": 35.0,
            "azimuth": 180.0
        }
        response = client.post("/forecast/systems", json=system_data, headers=headers1)
        assert response.status_code == 201
        system_id = response.json()["id"]
        
        # User1 can see their system
        response = client.get("/forecast/systems", headers=headers1)
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["id"] == system_id
        
        # User2 cannot see user1's system
        headers2 = {"Authorization": f"Bearer {user2_token}"}
        response = client.get("/forecast/systems", headers=headers2)
        assert response.status_code == 200
        assert len(response.json()) == 0  # Empty list
    
    def test_same_user_multiple_requests(self, client, valid_jwt_token):
        """Test that same user gets consistent user_id across requests"""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        
        # Create first system
        system1_data = {
            "name": "System 1",
            "latitude": 48.2082,
            "longitude": 16.3738,
            "kwp": 8.5,
            "tilt": 35.0,
            "azimuth": 180.0
        }
        response1 = client.post("/forecast/systems", json=system1_data, headers=headers)
        assert response1.status_code == 201
        user_id_1 = response1.json()["user_id"]
        
        # Create second system
        system2_data = {
            "name": "System 2",
            "latitude": 48.2100,
            "longitude": 16.3800,
            "kwp": 10.0,
            "tilt": 30.0,
            "azimuth": 200.0
        }
        response2 = client.post("/forecast/systems", json=system2_data, headers=headers)
        assert response2.status_code == 201
        user_id_2 = response2.json()["user_id"]
        
        # Both systems should have the same user_id
        assert user_id_1 == user_id_2
        
        # Get all systems for the user
        response = client.get("/forecast/systems", headers=headers)
        assert response.status_code == 200
        systems = response.json()
        assert len(systems) == 2
        assert all(system["user_id"] == user_id_1 for system in systems)


class TestUserAutoCreation:
    """Test user auto-creation functionality"""
    
    def test_user_auto_created_on_first_request(self, client, valid_jwt_token):
        """Test that user is automatically created on first authenticated request"""
        # Verify user doesn't exist initially
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == "test@example.com").first()
        db.close()
        assert user is None
        
        # Make authenticated request
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        response = client.get("/forecast/systems", headers=headers)
        assert response.status_code == 200
        
        # Verify user was created
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == "test@example.com").first()
        db.close()
        assert user is not None
        assert user.email == "test@example.com"
