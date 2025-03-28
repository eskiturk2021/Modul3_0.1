# api_gateway/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import os
from typing import List
from contextlib import asynccontextmanager
from services.websocket_service import websocket_service

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger = logging.getLogger(__name__)

# Импорты роутеров
from routers import dashboard, customers, appointments, documents, activity
from routers import settings as settings_router
from routers import auth
from config import settings
from middleware.auth import AuthMiddleware
from middleware.rate_limit import RateLimitMiddleware  # Добавьте этот middleware для защиты от DDoS

# Импорты для инициализации базы данных
from database.postgresql import Base, db_service
from database.models import User, Customer, Appointment, Service, Activity, Document, Conversation, AvailableSlot
from database.init_data import initialize_default_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Обработчик жизненного цикла приложения"""
    # Код, который выполняется при запуске
    logger.info("Запуск приложения...")
    try:
        # Проверяем и инициализируем данные по умолчанию при первом запуске
        initialize_default_data(db_service)
        logger.info("Инициализация данных завершена")
    except Exception as e:
        logger.error(f"Ошибка при инициализации данных: {str(e)}")

    yield  # Здесь приложение работает

    # Код, который выполняется при завершении
    logger.info("Завершение работы приложения...")


# Инициализация базы данных (создание таблиц, если они не существуют)
Base.metadata.create_all(bind=db_service.engine)

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Отключение автодокументации в продакшене
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)


# Middleware для логирования запросов с фильтрацией "шумных" запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Исключаем частые проверки работоспособности из логов для уменьшения шума
    if request.url.path not in ["/health"]:
        logger.info(f"Запрос: {request.method} {request.url}")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Также исключаем частые проверки из логов ответов
        if request.url.path not in ["/health"]:
            logger.info(f"Ответ: {response.status_code} за {process_time:.4f}с")
        return response
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {str(e)}")
        raise


# Настройка CORS с обработанным списком источников
# Добавляем middleware для аутентификации
app.add_middleware(
    AuthMiddleware,
    public_paths=[
        "/health",
        "/",
        "/api/auth/login",
        "/api/auth/refresh",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/test/config"
    ]
)

# Добавляем middleware для ограничения количества запросов (защита от DDoS)
app.add_middleware(
    RateLimitMiddleware,
    limit_per_minute=settings.RATE_LIMIT_PER_MINUTE
)

# Настройка CORS с обработанным списком источников
# Подготовка списка разрешенных источников
cors_origins = ["*"] if settings.CORS_ORIGINS == "*" else settings.CORS_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Эндпоинт для тестирования конфигурации (доступен только в режиме отладки)
@app.get("/test/config")
async def test_config():
    """Проверка конфигурации"""
    if not settings.DEBUG:
        return {"message": "This endpoint is only available in debug mode"}

    return {
        "DATABASE_URL": "***" if settings.DATABASE_URL else "Not set",  # Скрываем URL для безопасности
        "S3_BUCKET": settings.S3_BUCKET,
        "S3_REGION": settings.S3_REGION,
        "API_KEY": "***" if settings.API_KEY else "Not set",
        "PORT": settings.PORT,
        "ENV_PORT": os.getenv("PORT", "Not set"),
        "CORS_ORIGINS": settings.CORS_ORIGINS,
        "JWT_SECRET_KEY": "***" if settings.JWT_SECRET_KEY else "Not set"
    }

app.mount("/ws", websocket_service.app)

# Подключаем роутеры
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(customers.router, prefix="/api", tags=["customers"])
app.include_router(appointments.router, prefix="/api", tags=["appointments"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(settings_router.router, prefix="/api", tags=["settings"])
app.include_router(activity.router, prefix="/api", tags=["activity"])


@app.get("/health")
async def health_check():
    """Проверка работоспособности API"""
    try:
        # Проверяем соединение с базой данных
        with db_service.session_scope() as session:
            db_status = "connected"
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {str(e)}")
        db_status = f"error"

    try:
        # Проверяем соединение с S3
        from storage.s3_client import S3Service
        s3_service = S3Service(
            aws_access_key=settings.S3_AWS_ACCESS_KEY,
            aws_secret_key=settings.S3_AWS_SECRET_KEY,
            region=settings.S3_REGION,
            bucket=settings.S3_BUCKET,
            base_path=settings.S3_BASE_PATH
        )
        s3_status = "connected"
    except Exception as e:
        logger.error(f"Ошибка подключения к S3: {str(e)}")
        s3_status = f"error"

    return {
        "status": "healthy" if db_status == "connected" and s3_status == "connected" else "unhealthy",
        "database": db_status,
        "s3": s3_status,
        "timestamp": time.time()
    }


@app.get("/")
async def root():
    """Корневой маршрут для проверки работоспособности"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


# Middleware для обработки исключений
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Необработанное исключение: {str(exc)}", exc_info=True)
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"message": "Внутренняя ошибка сервера", "details": str(exc) if settings.DEBUG else None}
    )


if __name__ == "__main__":
    import uvicorn

    # Безопасная обработка порта с значением по умолчанию
    port = int(settings.PORT) if settings.PORT else 8000

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        access_log=settings.DEBUG
    )