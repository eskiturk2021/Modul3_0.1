# api_gateway/config.py
import os
from pydantic_settings import BaseSettings
import secrets


class Settings(BaseSettings):
    # JWT настройки - используем сложный случайный ключ, если не указан в окружении
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
    JWT_ALGORITHM: str = "HS256"
    JWT_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Добавлена новая настройка

    # API настройки - используем секретное окружение
    API_KEY: str = os.getenv("API_KEY", "default-api-key")

    # Настройки PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

    # Настройки пула соединений с БД
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))

    # Настройки S3 - используем имена переменных из Railway
    S3_AWS_ACCESS_KEY: str = os.getenv("AWS_ACCESS_KEY_ID", "dummy-access-key")
    S3_AWS_SECRET_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "dummy-secret-key")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_BUCKET: str = os.getenv("S3_BUCKET_NAME", "dummy-bucket")
    S3_BASE_PATH: str = os.getenv("S3_BASE_PATH", "user_data/")

    # CORS настройки - в продакшене указываем только нужные домены
    CORS_ORIGINS: list = [origin.strip() for origin in
                          os.getenv("CORS_ORIGINS", "http://modul4-production.up.railway.app").split(",")]

    # Настройки приложения
    APP_NAME: str = "Customer Management API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "API для интеграции дашборда с системой управления клиентами"

    # Railway автоматически устанавливает порт
    PORT: int = int(os.getenv("PORT", 8000))

    # Настройка для режима отладки - по умолчанию выключена в продакшене
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # Настройки кэширования
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # Время жизни кэша в секундах

    # Настройки безопасности
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT", "100"))  # Лимит запросов в минуту
    PASSWORD_SALT: str = os.getenv("PASSWORD_SALT", secrets.token_hex(16))

    # Настройки логирования
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Создаем экземпляр настроек
settings = Settings()