# api_gateway/middleware/rate_limit.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, List
import time


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int = 100):
        super().__init__(app)
        self.limit_per_minute = limit_per_minute
        self.request_counts: Dict[str, List[float]] = {}

    async def dispatch(self, request: Request, call_next):
        # Определяем IP-адрес клиента
        client_ip = request.client.host if request.client else "unknown"

        # Пропускаем ограничение для healthcheck
        if request.url.path == "/health":
            return await call_next(request)

        # Получаем текущие запросы для этого IP
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []

        # Текущее время
        current_time = time.time()

        # Очищаем старые запросы (старше 60 секунд)
        self.request_counts[client_ip] = [
            t for t in self.request_counts[client_ip]
            if current_time - t < 60
        ]

        # Проверяем лимит
        if len(self.request_counts[client_ip]) >= self.limit_per_minute:
            return HTTPException(
                status_code=429,
                detail="Too many requests"
            )

        # Добавляем новый запрос
        self.request_counts[client_ip].append(current_time)

        # Продолжаем обработку запроса
        return await call_next(request)