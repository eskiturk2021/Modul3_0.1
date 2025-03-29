# api_gateway/middleware/cors.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from typing import List

logger = logging.getLogger(__name__)


class CustomCORSMiddleware(BaseHTTPMiddleware):
    """
    Единая middleware для обработки CORS с улучшенным логированием
    """

    def __init__(self, app, allowed_origins: List[str]):
        super().__init__(app)
        self.allowed_origins = allowed_origins
        logger.info(f"Инициализирована CustomCORSMiddleware с разрешенными источниками: {allowed_origins}")

    async def dispatch(self, request: Request, call_next):
        # Логирование всех входящих запросов для отладки CORS
        origin = request.headers.get("Origin")
        method = request.method
        path = request.url.path

        logger.debug(f"CORS: {method} запрос от {origin} к {path}")

        # Для OPTIONS (preflight) запросов возвращаем сразу ответ с заголовками CORS
        if method == "OPTIONS":
            logger.info(f"Обработка OPTIONS запроса от {origin} к {path}")

            if origin and origin in self.allowed_origins:
                logger.info(f"Источник {origin} разрешен")
            else:
                logger.warning(f"Источник {origin} не найден в списке разрешенных: {self.allowed_origins}")

            response = Response()
            # Устанавливаем CORS заголовки
            self._set_cors_headers(response, origin)
            # Для префлайт-запросов добавляем дополнительную информацию
            response.headers["Access-Control-Max-Age"] = "3600"  # Кэширование preflight на час

            # Логирование отправляемых заголовков
            logger.debug(f"Отправка заголовков OPTIONS: {dict(response.headers)}")
            return response

        # Для не-OPTIONS запросов обрабатываем обычным образом
        response = await call_next(request)

        # Добавляем CORS заголовки к ответу
        self._set_cors_headers(response, origin)

        return response

    def _set_cors_headers(self, response: Response, origin: str = None):
        """Установка всех необходимых CORS заголовков"""
        # Если источник в списке разрешенных, устанавливаем его, иначе используем первый из списка
        if origin and origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        elif self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = self.allowed_origins[0]

        # Общие заголовки CORS
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers[
            "Access-Control-Allow-Headers"] = "X-API-Key, Authorization, Content-Type, Accept, Origin, X-Requested-With"