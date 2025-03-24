# api_gateway/middleware/auth.py
import jwt
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, List, Dict, Any
from datetime import datetime

from config import settings

# Заголовок для API-ключа
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")
security = HTTPBearer()

# API-ключ из настроек
API_KEY = settings.API_KEY


async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """
    Проверяет API-ключ в заголовке запроса
    """
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Недействительный API-ключ"
        )
    return api_key


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Зависимость для получения текущего пользователя из JWT-токена
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if payload.get("exp") < datetime.utcnow().timestamp():
            raise HTTPException(status_code=401, detail="Token has expired")

        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


def is_admin(user: Dict[str, Any] = Depends(get_current_user)) -> bool:
    """
    Проверяет, является ли пользователь администратором
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return True


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware для комбинированной аутентификации по API-ключу и JWT-токену
    """

    def __init__(self, app, public_paths: List[str] = None):
        super().__init__(app)
        self.public_paths = public_paths or ["/health", "/", "/api/auth/login", "/api/auth/refresh"]
        self.algorithm = settings.JWT_ALGORITHM
        self.secret_key = settings.JWT_SECRET_KEY

    async def dispatch(self, request: Request, call_next):

        # Пропускаем проверку API ключа для OPTIONS запросов (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Проверяем наличие API-ключа во всех запросах
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != API_KEY:
            return HTMLResponse(
                status_code=403,
                content="Unauthorized: Invalid API key"
            )

        # Для публичных путей достаточно проверки API-ключа
        if any(request.url.path.startswith(path) for path in self.public_paths):
            return await call_next(request)

        # Для защищенных путей проверяем также JWT-токен
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return HTMLResponse(
                status_code=401,
                content="Unauthorized: Missing JWT token"
            )

        try:
            token = auth_header.split("Bearer ")[1] if "Bearer " in auth_header else None
            if not token:
                return HTMLResponse(
                    status_code=401,
                    content="Unauthorized: Invalid authorization format"
                )

            # Верифицируем токен
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Проверяем срок действия токена
            if payload.get("exp") < datetime.utcnow().timestamp():
                return HTMLResponse(
                    status_code=401,
                    content="Unauthorized: Token has expired"
                )

            # Добавляем пользовательские данные в запрос
            request.state.user = payload
        except jwt.PyJWTError as e:
            return HTMLResponse(
                status_code=401,
                content=f"Unauthorized: Invalid JWT token - {str(e)}"
            )

        # Если все проверки пройдены, продолжаем обработку запроса
        return await call_next(request)