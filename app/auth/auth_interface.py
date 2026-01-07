from abc import ABC, abstractmethod
from typing import Optional
from ..models import User


class AuthServiceInterface(ABC):
    @abstractmethod
    async def authenticate(self, token: str) -> Optional[User]:
        pass
    
    @abstractmethod
    async def get_current_user(self, token: str) -> Optional[User]:
        pass