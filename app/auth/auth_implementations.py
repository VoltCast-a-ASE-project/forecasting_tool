import os
from typing import Optional
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from .auth_interface import AuthServiceInterface


class JWTAuthService(AuthServiceInterface):
    def __init__(self, db_session: Session = None):
        self.db_session = db_session or next(get_db())
    
    async def authenticate(self, token: str) -> Optional[User]:
        # TODO: Implement real JWT validation using API Gateway
        # For now, this will be implemented when integrating with gateway
        return None
    
    async def get_current_user(self, token: str) -> Optional[User]:
        # TODO: Implement real JWT validation and user lookup
        return None


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