import os
import uuid
import jwt
from typing import Optional
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from .auth_interface import AuthServiceInterface


class JWTAuthService(AuthServiceInterface):
    def __init__(self, db_session: Session = None):
        self.db_session = db_session or next(get_db())
        self.jwt_secret = os.getenv("JWT_SECRET", "default-secret-key")
        self.algorithm = os.getenv("ALGORITHM", "HS256")
    
    async def authenticate(self, token: str) -> Optional[User]:
        try:
            # JWT token validieren und payload extrahieren
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.algorithm])
            username = payload.get("sub")
            
            if not username:
                return None
                
            # Benutzer in lokaler DB finden
            user = self.db_session.query(User).filter(User.email == username).first()
            
            # Wenn Benutzer nicht existiert, neuen anlegen
            if not user:
                user = User(
                    id=str(uuid.uuid4()),
                    email=username
                )
                self.db_session.add(user)
                self.db_session.commit()
                self.db_session.refresh(user)
            
            return user
            
        except jwt.ExpiredSignatureError:
            # Token abgelaufen
            return None
        except jwt.InvalidTokenError:
            # Token ungültig
            return None
        except Exception:
            # Andere Fehler
            return None
    
    async def get_current_user(self, token: str) -> Optional[User]:
        return await self.authenticate(token)


class MockAuthService(AuthServiceInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    async def authenticate(self, token: str) -> Optional[User]:
        # Mock authentication for testing
        if token.startswith("mock-token-for-"):
            user_id = token.replace("mock-token-for-", "")
            user = self.db_session.query(User).filter(User.id == user_id).first()
            return user
        return None
    
    async def get_current_user(self, token: str) -> Optional[User]:
        return await self.authenticate(token)


def get_auth_service(db_session: Session) -> AuthServiceInterface:
    """Factory function to get the appropriate auth service based on environment"""
    if os.getenv("TESTING", "false").lower() == "true":
        return MockAuthService(db_session)
    else:
        return JWTAuthService(db_session)