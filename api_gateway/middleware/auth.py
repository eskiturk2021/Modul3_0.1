# api_gateway/middleware/auth.py
import jwt
import traceback
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from config import settings

logger = logging.getLogger(__name__)

# Заголовок для API-ключа
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")
security = HTTPBearer()

# API-ключ из настроек
API_KEY = settings.API_KEY
logger.info(f"API-ключ настроен: {'Да' if API_KEY else 'Нет'}")


async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """
    Проверяет API-ключ в заголовке запроса
    """
    logger.debug(
        f"Проверка API-ключа в verify_api_key: предоставленный ключ {'присутствует' if api_key else 'отсутствует'}")
    if api_key != API_KEY:
        logger.warning("Недействительный API-ключ в verify_api_key")
        raise HTTPException(
            status_code=403,
            detail="Недействительный API-ключ"
        )
    logger.debug("API-ключ успешно проверен в verify_api_key")
    return api_key


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Зависимость для получения текущего пользователя из JWT-токена
    """
    logger.debug("Получение пользователя из JWT-токена")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        logger.debug(f"JWT токен декодирован успешно. Пользователь: {payload.get('username', 'не указан')}")

        if payload.get("exp") < datetime.utcnow().timestamp():
            logger.warning("JWT токен истек")
            raise HTTPException(status_code=401, detail="Token has expired")

        return payload
    except jwt.PyJWTError as e:
        logger.error(f"Ошибка JWT при проверке токена: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


def is_admin(user: Dict[str, Any] = Depends(get_current_user)) -> bool:
    """
    Проверяет, является ли пользователь администратором
    """
    logger.debug(f"Проверка прав администратора для пользователя {user.get('username', 'неизвестно')}")
    if user.get("role") != "admin":
        logger.warning(f"Отказано в доступе пользователю {user.get('username')}: не является администратором")
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    logger.debug(f"Пользователь {user.get('username')} подтвержден как администратор")
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
        logger.info(f"Инициализация AuthMiddleware с {len(self.public_paths)} публичными путями")
        logger.debug(f"Публичные пути: {', '.join(self.public_paths)}")

    async def dispatch(self, request: Request, call_next):
        request_path = request.url.path
        request_method = request.method
        logger.debug(f"AuthMiddleware: {request_method} {request_path}")

        # Пропускаем проверку API ключа для OPTIONS запросов (CORS preflight)
        if request_method == "OPTIONS":
            logger.debug(f"Пропуск проверки для OPTIONS запроса: {request_path}")
            return await call_next(request)

        # Для публичных путей достаточно проверки API-ключа
        if any(request_path.startswith(path) for path in self.public_paths):
            logger.debug(f"Публичный путь {request_path}: пропуск проверки JWT")
            return await call_next(request)

        # Проверяем наличие API-ключа во всех запросах
        api_key = request.headers.get("X-API-Key")
        logger.debug(f"API-ключ {'предоставлен' if api_key else 'не предоставлен'} для {request_path}")

        if not api_key or api_key != API_KEY:
            logger.warning(f"Недействительный API-ключ для запроса {request_path}")
            return HTMLResponse(
                status_code=403,
                content="Unauthorized: Invalid API key"
            )

        # Для защищенных путей проверяем также JWT-токен
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"Отсутствует JWT-токен для защищенного пути {request_path}")
            return HTMLResponse(
                status_code=401,
                content="Unauthorized: Missing JWT token"
            )

        try:
            if "Bearer " not in auth_header:
                logger.warning(f"Неверный формат заголовка авторизации: {auth_header}")
                return HTMLResponse(
                    status_code=401,
                    content="Unauthorized: Invalid authorization format"
                )

            token = auth_header.split("Bearer ")[1]
            logger.debug(f"Получен JWT-токен для проверки: {token[:10]}...")

            # Верифицируем токен
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            logger.debug(f"JWT-токен успешно декодирован. Пользователь: {payload.get('username', 'не указан')}")

            # Проверяем срок действия токена
            if payload.get("exp") < datetime.utcnow().timestamp():
                exp_time = datetime.fromtimestamp(payload.get("exp")).isoformat()
                logger.warning(f"JWT-токен истек для {request_path}. Срок действия: {exp_time}")
                return HTMLResponse(
                    status_code=401,
                    content="Unauthorized: Token has expired"
                )

            # Добавляем пользовательские данные в запрос
            request.state.user = payload
            logger.debug(f"Пользователь {payload.get('username')} аутентифицирован для {request_path}")

        except jwt.PyJWTError as e:
            logger.error(f"Ошибка JWT для {request_path}: {str(e)}")
            logger.error(traceback.format_exc())
            return HTMLResponse(
                status_code=401,
                content=f"Unauthorized: Invalid JWT token - {str(e)}"
            )
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при проверке JWT для {request_path}: {str(e)}")
            logger.error(traceback.format_exc())
            return HTMLResponse(
                status_code=401,
                content=f"Unauthorized: Error processing JWT token - {str(e)}"
            )

        # Если все проверки пройдены, продолжаем обработку запроса
        logger.debug(f"Авторизация успешна для {request_path}")
        return await call_next(request)