# api_gateway/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
import jwt
from typing import Optional, Dict, Any
from pydantic import BaseModel

from ..config import settings
from ..services.auth_service import AuthService
from ..dependencies import get_auth_service

router = APIRouter()


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/auth/login", response_model=TokenResponse)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        auth_service: AuthService = Depends(get_auth_service)
):
    try:
        token_data = auth_service.authenticate_user(form_data.username, form_data.password)
        if not token_data:
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")

        return TokenResponse(
            token=token_data["access_token"],
            expires_in=token_data["expires_in"]
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Ошибка при входе в систему: {str(e)}")


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
        refresh_data: RefreshRequest = Body(...),
        auth_service: AuthService = Depends(get_auth_service)
):
    try:
        token_data = auth_service.refresh_token(refresh_data.refresh_token)
        if not token_data:
            raise HTTPException(status_code=401, detail="Недействительный токен обновления")

        return TokenResponse(
            token=token_data["access_token"],
            expires_in=token_data["expires_in"]
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Недействительный токен: {str(e)}")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении токена: {str(e)}")


@router.get("/auth/me", response_model=Dict[str, Any])
async def get_current_user(
        auth_service: AuthService = Depends(get_auth_service),
        current_user: Dict[str, Any] = Depends(AuthService.get_current_user)
):
    """
    Получение информации о текущем пользователе
    """
    return current_user


@router.post("/auth/change-password", response_model=Dict[str, Any])
async def change_password(
        password_data: Dict[str, str] = Body(...),
        auth_service: AuthService = Depends(get_auth_service),
        current_user: Dict[str, Any] = Depends(AuthService.get_current_user)
):
    """
    Изменение пароля пользователя
    """
    try:
        if "old_password" not in password_data or "new_password" not in password_data:
            raise HTTPException(status_code=400, detail="Не указан старый или новый пароль")

        success = auth_service.change_password(
            user_id=current_user["id"],
            old_password=password_data["old_password"],
            new_password=password_data["new_password"]
        )

        if not success:
            raise HTTPException(status_code=400, detail="Неверный текущий пароль")

        return {
            "status": "success",
            "message": "Пароль успешно изменен"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при изменении пароля: {str(e)}")