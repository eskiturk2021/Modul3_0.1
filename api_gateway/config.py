# api_gateway/config.py
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT настройки
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY",
                                    "your-secret-key-for-development-only-please-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_TOKEN_EXPIRE_MINUTES: int = 30

    # API настройки
    API_KEY: str = os.getenv("API_KEY", "BD7FpLQr9X54zHtN6K8ESvcA3m2YgJxW")

    # Настройки PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://username:password@localhost:5432/database")

    # Настройки S3
    S3_AWS_ACCESS_KEY: str = os.getenv("S3_AWS_ACCESS_KEY", "")
    S3_AWS_SECRET_KEY: str = os.getenv("S3_AWS_SECRET_KEY", "")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "your-bucket-name")
    S3_BASE_PATH: str = os.getenv("S3_BASE_PATH", "user_data/")

    # CORS настройки
    CORS_ORIGINS: list = ["*"]
    # В продакшене лучше указать конкретные домены:
    # CORS_ORIGINS: list = [
    #    "https://your-frontend-domain.com",
    #    "https://dashboard.your-frontend-domain.com"
    # ]

    # Настройки приложения
    APP_NAME: str = "Customer Management API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "API для интеграции дашборда с системой управления клиентами"

    # Railway автоматически устанавливает порт
    PORT: int = int(os.getenv("PORT", 8000))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаем экземпляр настроек
settings = Settings()