# api_gateway/main.py с добавленным логированием
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import os
import traceback
from typing import List
from contextlib import asynccontextmanager
from services.websocket_service import websocket_service
from sqlalchemy import text

# Настройка логирования
logging_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO"))
logging.basicConfig(
    level=logging_level,
    format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api_gateway.log')  # Сохраняем логи в файл
    ]
)
logger = logging.getLogger(__name__)

# Импорты роутеров
from routers import dashboard, customers, appointments, documents, activity
from routers import settings as settings_router
from routers import auth
from config import settings
from middleware.auth import AuthMiddleware
from middleware.rate_limit import RateLimitMiddleware

# Импорты для инициализации базы данных
from database.postgresql import Base, db_service
from database.models import User, Customer, Appointment, Service, Activity, Document, Conversation, AvailableSlot
from database.init_data import initialize_default_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Обработчик жизненного цикла приложения"""
    # Код, который выполняется при запуске
    logger.info("=== Запуск приложения ===")
    logger.info(f"Версия приложения: {settings.APP_VERSION}")
    logger.info(f"Режим отладки: {settings.DEBUG}")
    logger.info(f"Порт: {settings.PORT}")
    logger.info(
        f"Строка подключения к БД: {settings.DATABASE_URL.replace(':'.join(settings.DATABASE_URL.split(':')[2:]), '***')}")

    try:
        logger.info("Проверка соединения с базой данных...")
        with db_service.session_scope() as session:
            result = session.execute(text("SELECT 1")).scalar()
            if result == 1:
                logger.info("Соединение с базой данных установлено успешно")
            else:
                logger.error("Ошибка при проверке соединения с базой данных")
    except Exception as e:
        logger.error(f"Ошибка при подключении к базе данных: {str(e)}")
        logger.error(traceback.format_exc())

    try:
        # Проверяем и инициализируем данные по умолчанию при первом запуске
        logger.info("Начало инициализации данных...")
        initialize_default_data(db_service)
        logger.info("Инициализация данных завершена")
    except Exception as e:
        logger.error(f"Ошибка при инициализации данных: {str(e)}")
        logger.error(traceback.format_exc())

    yield  # Здесь приложение работает

    # Код, который выполняется при завершении
    logger.info("=== Завершение работы приложения ===")
    logger.info("Закрытие соединений и освобождение ресурсов...")
    try:
        # Закрываем соединения с БД
        logger.info("Закрытие соединений с базой данных...")
        # Если есть какой-то специальный код для закрытия соединений, он должен быть здесь
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединений: {str(e)}")
        logger.error(traceback.format_exc())


# Инициализация базы данных (создание таблиц, если они не существуют)
try:
    logger.info("Создание таблиц базы данных, если они не существуют...")
    Base.metadata.create_all(bind=db_service.engine)
    logger.info("Таблицы базы данных созданы/проверены успешно")
except Exception as e:
    logger.error(f"Ошибка при создании таблиц базы данных: {str(e)}")
    logger.error(traceback.format_exc())

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Отключение автодокументации в продакшене
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)

@app.middleware("http")
async def log_cors_details(request: Request, call_next):
    if request.method == "OPTIONS":
        logger.info(f"CORS Preflight запрос от {request.headers.get('Origin')} к {request.url.path}")
        logger.info(f"CORS разрешенные источники: {cors_origins}")

    response = await call_next(request)

    if request.method == "OPTIONS":
        logger.info(f"CORS Preflight ответ: {response.status_code}")
        logger.info(
            f"CORS заголовки ответа: Access-Control-Allow-Origin={response.headers.get('Access-Control-Allow-Origin')}")

    return response

# Middleware для логирования запросов с фильтрацией "шумных" запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_id = f"req-{time.time()}"

    # Исключаем частые проверки работоспособности из логов для уменьшения шума
    if request.url.path not in ["/health"]:
        logger.info(f"[{request_id}] Запрос: {request.method} {request.url}")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Также исключаем частые проверки из логов ответов
        if request.url.path not in ["/health"]:
            logger.info(f"[{request_id}] Ответ: {response.status_code} за {process_time:.4f}с")
        return response
    except Exception as e:
        logger.error(f"[{request_id}] Ошибка обработки запроса: {str(e)}")
        logger.error(traceback.format_exc())
        raise


# Добавляем middleware для аутентификации
try:
    logger.info("Настройка middleware для аутентификации...")
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
    logger.info("Middleware для аутентификации настроен успешно")
except Exception as e:
    logger.error(f"Ошибка при настройке middleware для аутентификации: {str(e)}")
    logger.error(traceback.format_exc())

# Добавляем middleware для ограничения количества запросов (защита от DDoS)
try:
    logger.info("Настройка middleware для ограничения запросов...")
    app.add_middleware(
        RateLimitMiddleware,
        limit_per_minute=settings.RATE_LIMIT_PER_MINUTE
    )
    logger.info("Middleware для ограничения запросов настроен успешно")
except Exception as e:
    logger.error(f"Ошибка при настройке middleware для ограничения запросов: {str(e)}")
    logger.error(traceback.format_exc())

# Настройка CORS с обработанным списком источников
# Подготовка списка разрешенных источников
# Исправьте этот код в main.py
if settings.CORS_ORIGINS == "*":
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

# Если мы хотим использовать только один конкретный домен
cors_origins = ["https://modul4-production.up.railway.app"]

try:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["X-API-Key", "Authorization", "Content-Type", "Accept"],
    )
    logger.info("CORS middleware настроен успешно")
except Exception as e:
    logger.error(f"Ошибка при настройке CORS middleware: {str(e)}")
    logger.error(traceback.format_exc())


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


try:
    logger.info("Настройка WebSocket...")
    app.mount("/ws", websocket_service.app)
    logger.info("WebSocket настроен успешно")
except Exception as e:
    logger.error(f"Ошибка при настройке WebSocket: {str(e)}")
    logger.error(traceback.format_exc())

# Подключаем роутеры
try:
    logger.info("Подключение роутеров...")
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
    app.include_router(customers.router, prefix="/api", tags=["customers"])
    app.include_router(appointments.router, prefix="/api", tags=["appointments"])
    app.include_router(documents.router, prefix="/api", tags=["documents"])
    app.include_router(settings_router.router, prefix="/api", tags=["settings"])
    app.include_router(activity.router, prefix="/api", tags=["activity"])
    logger.info("Все роутеры подключены успешно")
except Exception as e:
    logger.error(f"Ошибка при подключении роутеров: {str(e)}")
    logger.error(traceback.format_exc())


@app.get("/health")
async def health_check():
    """Проверка работоспособности API"""
    db_status = "unknown"
    s3_status = "unknown"

    try:
        # Проверяем соединение с базой данных
        logger.debug("Выполнение проверки соединения с БД в /health")
        with db_service.session_scope() as session:
            result = session.execute(text("SELECT 1")).scalar()
            db_status = "connected" if result == 1 else "error"
            logger.debug(f"Результат проверки БД: {db_status}")
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {str(e)}")
        db_status = f"error: {str(e)[:100]}"  # Обрезаем длинные сообщения об ошибках

    try:
        # Проверяем соединение с S3
        logger.debug("Выполнение проверки соединения с S3 в /health")
        from storage.s3_client import S3Service
        s3_service = S3Service(
            aws_access_key=settings.S3_AWS_ACCESS_KEY,
            aws_secret_key=settings.S3_AWS_SECRET_KEY,
            region=settings.S3_REGION,
            bucket=settings.S3_BUCKET,
            base_path=settings.S3_BASE_PATH
        )
        # Легкая проверка без обращения к бакету
        if s3_service.s3_client:
            s3_status = "connected"
        logger.debug(f"Результат проверки S3: {s3_status}")
    except Exception as e:
        logger.error(f"Ошибка подключения к S3: {str(e)}")
        s3_status = f"error: {str(e)[:100]}"  # Обрезаем длинные сообщения об ошибках

    overall_status = "healthy" if db_status == "connected" and s3_status == "connected" else "unhealthy"
    logger.debug(f"Результат проверки /health: {overall_status}")

    return {
        "status": overall_status,
        "database": db_status,
        "s3": s3_status,
        "timestamp": time.time()
    }


@app.get("/")
async def root():
    """Корневой маршрут для проверки работоспособности"""
    logger.debug("Запрос к корневому маршруту /")
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
    logger.info(f"Запуск сервера на порту {port}")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        access_log=settings.DEBUG
    )