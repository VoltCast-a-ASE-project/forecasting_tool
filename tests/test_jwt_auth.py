import pytest
import asyncio
import os
import jwt
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.auth.auth_implementations import JWTAuthService
from app.models import User


@pytest.fixture
def db_session():
    """Create a test database session"""
    # Import here to avoid circular imports
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import Base
    
    # In-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def jwt_service(db_session):
    """Create JWTAuthService instance for testing"""
    # Clear environment variables first
    for key in ["JWT_SECRET", "ALGORITHM"]:
        if key in os.environ:
            del os.environ[key]
    return JWTAuthService(db_session)


@pytest.fixture
def jwt_service_with_env(db_session):
    """Create JWTAuthService with test environment variables"""
    os.environ["JWT_SECRET"] = "test-secret-key"
    os.environ["ALGORITHM"] = "HS256"
    return JWTAuthService(db_session)


@pytest.fixture
def valid_token():
    """Create a valid JWT token for testing"""
    secret = "test-secret-key"
    algorithm = "HS256"
    payload = {
        "sub": "test@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, secret, algorithm)


@pytest.fixture
def expired_token():
    """Create an expired JWT token for testing"""
    secret = "test-secret-key"
    algorithm = "HS256"
    payload = {
        "sub": "test@example.com",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
        "iat": datetime.now(timezone.utc) - timedelta(hours=2)
    }
    return jwt.encode(payload, secret, algorithm)


@pytest.fixture
def invalid_token():
    """Create an invalid JWT token for testing"""
    return "this.is.not.a.valid.jwt.token"


class TestJWTAuthService:
    """Test cases for JWTAuthService"""
    
    def test_init_with_default_values(self, db_session):
        """Test JWTAuthService initialization with default values"""
        # Clear environment variables
        old_secret = os.environ.get("JWT_SECRET")
        old_algorithm = os.environ.get("ALGORITHM")
        
        if "JWT_SECRET" in os.environ:
            del os.environ["JWT_SECRET"]
        if "ALGORITHM" in os.environ:
            del os.environ["ALGORITHM"]
        
        service = JWTAuthService(db_session)
        
        assert service.jwt_secret == "default-secret-key"
        assert service.algorithm == "HS256"
        
        # Restore environment variables
        if old_secret:
            os.environ["JWT_SECRET"] = old_secret
        if old_algorithm:
            os.environ["ALGORITHM"] = old_algorithm
    
    def test_init_with_env_variables(self, db_session):
        """Test JWTAuthService initialization with environment variables"""
        os.environ["JWT_SECRET"] = "custom-secret"
        os.environ["ALGORITHM"] = "HS256"
        
        service = JWTAuthService(db_session)
        
        assert service.jwt_secret == "custom-secret"
        assert service.algorithm == "HS256"
    
    def test_authenticate_valid_token_creates_user(self, jwt_service_with_env, valid_token):
        """Test that valid token creates a new user if not exists"""
        # Verify user doesn't exist initially
        user = jwt_service_with_env.db_session.query(User).filter(User.email == "test@example.com").first()
        assert user is None
        
        # Authenticate with valid token
        user = asyncio.run(jwt_service_with_env.authenticate(valid_token))
        
        assert user is not None
        assert user.email == "test@example.com"
        assert user.id is not None
        
        # Verify user was created in database
        db_user = jwt_service_with_env.db_session.query(User).filter(User.email == "test@example.com").first()
        assert db_user is not None
        assert db_user.id == user.id
    
    def test_authenticate_valid_token_returns_existing_user(self, jwt_service_with_env, valid_token, db_session):
        """Test that valid token returns existing user"""
        # Create user manually
        existing_user = User(id="pre-existing-user", email="test@example.com")
        db_session.add(existing_user)
        db_session.commit()
        
        # Authenticate with valid token
        user = asyncio.run(jwt_service_with_env.authenticate(valid_token))
        
        assert user is not None
        assert user.email == "test@example.com"
        assert user.id == "pre-existing-user"  # Should return existing user
    
    def test_authenticate_expired_token(self, jwt_service_with_env, expired_token):
        """Test that expired token returns None"""
        user = asyncio.run(jwt_service_with_env.authenticate(expired_token))
        assert user is None
    
    def test_authenticate_invalid_token(self, jwt_service_with_env, invalid_token):
        """Test that invalid token returns None"""
        user = asyncio.run(jwt_service_with_env.authenticate(invalid_token))
        assert user is None
    
    def test_authenticate_token_without_subject(self, jwt_service_with_env):
        """Test that token without 'sub' claim returns None"""
        # Create token without subject
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc)
        }
        token = jwt.encode(payload, "test-secret-key", "HS256")
        
        user = asyncio.run(jwt_service_with_env.authenticate(token))
        assert user is None
    
    def test_authenticate_wrong_secret(self, valid_token):
        """Test that token with wrong secret returns None"""
        os.environ["JWT_SECRET"] = "wrong-secret"
        os.environ["ALGORITHM"] = "HS256"
        
        from app.auth.auth_implementations import JWTAuthService
        from app.database import get_db
        db = next(get_db())
        service = JWTAuthService(db)
        
        user = asyncio.run(service.authenticate(valid_token))
        assert user is None
    
    def test_get_current_user_same_as_authenticate(self, jwt_service_with_env, valid_token):
        """Test that get_current_user returns same result as authenticate"""
        auth_user = asyncio.run(jwt_service_with_env.authenticate(valid_token))
        current_user = asyncio.run(jwt_service_with_env.get_current_user(valid_token))
        
        assert auth_user is not None
        assert current_user is not None
        assert auth_user.id == current_user.id
        assert auth_user.email == current_user.email