# api_gateway/repositories/user_repository.py
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from repositories.base_repository import BaseRepository
from database.models import User


class UserRepository(BaseRepository[User]):
    def __init__(self, session: Session):
        super().__init__(User, session)

    def get_by_username(self, username: str) -> Optional[User]:
        """Получает пользователя по имени пользователя"""
        return self.session.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Получает пользователя по email"""
        return self.session.query(User).filter(User.email == email).first()

    def get_by_refresh_token(self, refresh_token: str) -> Optional[User]:
        """Получает пользователя по токену обновления"""
        return self.session.query(User).filter(User.refresh_token == refresh_token).first()

    def get_active_users(self, limit: int = 20) -> List[User]:
        """Получает список активных пользователей"""
        return self.session.query(User).filter(User.is_active == True).limit(limit).all()

    def get_by_role(self, role: str, limit: int = 20) -> List[User]:
        """Получает пользователей по роли"""
        return self.session.query(User).filter(User.role == role).limit(limit).all()