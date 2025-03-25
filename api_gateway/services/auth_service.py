# services/auth_service.py
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
import hashlib
from fastapi import Depends, HTTPException

from repositories.user_repository import UserRepository
from config import settings


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_TOKEN_EXPIRE_MINUTES

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Аутентификация пользователя по логину и паролю"""
        with self.user_repo.session_scope() as session:
            user_repo = UserRepository(session)
            user = user_repo.get_by_username(username)

            if not user:
                return None

            # Проверяем пароль (хеширование)
            hashed_password = self._hash_password(password)
            if user.password != hashed_password:
                return None

            # Создаем JWT токен
            access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
            access_token = self._create_access_token(
                data={
                    "sub": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "role": user.role
                },
                expires_delta=access_token_expires
            )

            # Обновляем время последнего входа
            user_repo.update(user.id, {"last_login": datetime.utcnow()})

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60  # в секундах
            }

    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Обновление JWT токена"""
        try:
            # Декодируем токен без проверки истечения
            payload = jwt.decode(
                refresh_token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )

            # Получаем пользователя
            user_id = payload.get("sub")
            if not user_id:
                return None

            with self.user_repo.session_scope() as session:
                user_repo = UserRepository(session)
                user = user_repo.get_by_id(int(user_id))

                if not user:
                    return None

                # Создаем новый токен
                access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
                access_token = self._create_access_token(
                    data={
                        "sub": str(user.id),
                        "username": user.username,
                        "email": user.email,
                        "role": user.role
                    },
                    expires_delta=access_token_expires
                )

                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "expires_in": self.access_token_expire_minutes * 60  # в секундах
                }

        except jwt.PyJWTError:
            return None

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Изменение пароля пользователя"""
        with self.user_repo.session_scope() as session:
            user_repo = UserRepository(session)
            user = user_repo.get_by_id(user_id)

            if not user:
                return False

            # Проверяем старый пароль
            if user.password != self._hash_password(old_password):
                return False

            # Обновляем пароль
            user_repo.update(user_id, {"password": self._hash_password(new_password)})
            return True

    def _create_access_token(self, data: Dict[str, Any], expires_delta: timedelta) -> str:
        """Создание JWT токена"""
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def _hash_password(self, password: str) -> str:
        """Хеширование пароля"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def get_current_user(authorization: str = Depends(lambda x: x.headers.get("Authorization"))):
        """Получение текущего пользователя из JWT токена"""
        if not authorization or "Bearer " not in authorization:
            raise HTTPException(status_code=401, detail="Не предоставлен токен")

        token = authorization.split("Bearer ")[1]

        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return {
                "id": payload.get("sub"),
                "username": payload.get("username"),
                "email": payload.get("email"),
                "role": payload.get("role")
            }
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Недействительный токен")