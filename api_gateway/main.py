# api_gateway/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import os
from typing import List

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорты роутеров
from routers import dashboard, customers, appointments, documents, activity
from routers import settings as settings_router
from routers import auth
from config import settings
from middleware.auth import AuthMiddleware

# Импорты для инициализации базы данных
from database.postgresql import Base, db_service
from database.models import User, Customer, Appointment, Service, Document, Activity, Conversation, AvailableSlot

# Инициализация базы данных (создание таблиц, если они не существуют)
Base.metadata.create_all(bind=db_service.engine)

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION
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


# Проверяем формат CORS_ORIGINS и приводим к нужному типу
allowed_origins: List[str] = settings.CORS_ORIGINS
if isinstance(allowed_origins, str):
    # Если это строка с разделителями, преобразуем в список
    allowed_origins = [origin.strip() for origin in allowed_origins.split(",")]
elif not isinstance(allowed_origins, list):
    # Если это не список, используем значения по умолчанию
    allowed_origins = ["https://modul4-production.up.railway.app", "http://localhost:3000"]

# Настройка CORS с обработанным списком источников
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# Эндпоинт для тестирования конфигурации
@app.get("/test/config")
async def test_config():
    """Проверка конфигурации"""
    return {
        "DATABASE_URL": "***" if settings.DATABASE_URL else "Not set",  # Скрываем URL для безопасности
        "S3_BUCKET": settings.S3_BUCKET,
        "S3_REGION": settings.S3_REGION,
        "API_KEY": "***" if settings.API_KEY else "Not set",
        "PORT": settings.PORT,
        "ENV_PORT": os.getenv("PORT", "Not set"),
        "CORS_ORIGINS": allowed_origins,
        "JWT_SECRET_KEY": "***" if settings.JWT_SECRET_KEY else "Not set"
    }


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
        db_status = f"error: {str(e)}"

    try:
        # Проверяем соединение с S3
        from storage.s3_client import s3_service
        s3_status = "connected"
    except Exception as e:
        logger.error(f"Ошибка подключения к S3: {str(e)}")
        s3_status = f"error: {str(e)}"

    return {
        "status": "healthy",
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
        "description": settings.APP_DESCRIPTION,
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


# Инициализация данных при первом запуске (если нужно)
from database.init_data import initialize_default_data


@app.on_event("startup")
async def startup_event():
    logger.info("Запуск приложения...")
    try:
        # Проверяем и инициализируем данные по умолчанию при первом запуске
        initialize_default_data(db_service)
        logger.info("Инициализация данных завершена")
    except Exception as e:
        logger.error(f"Ошибка при инициализации данных: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Завершение работы приложения...")


if __name__ == "__main__":
    import uvicorn

    # Параметр DEBUG для отображения деталей ошибок (в продакшене должен быть False)
    settings.DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # Более безопасный вывод в логи (скрываем конфиденциальную информацию)
    logger.info(f"Запуск приложения на порту {settings.PORT}")

    # Безопасная обработка порта с значением по умолчанию
    port = int(settings.PORT) if settings.PORT else 8000

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "False").lower() in ("true", "1", "t")
    )