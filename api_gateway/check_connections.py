# api_gateway/check_connections.py
import os
import sys
import logging
from database.postgresql import DatabaseService
from storage.s3_client import S3Service
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_database():
    """Проверяет соединение с базой данных PostgreSQL"""
    logger.info("Проверка соединения с базой данных...")
    try:
        db_service = DatabaseService(settings.DATABASE_URL)
        with db_service.session_scope() as session:
            result = session.execute("SELECT 1").scalar()
            if result == 1:
                logger.info("Соединение с базой данных установлено успешно")
                return True
            else:
                logger.error("Ошибка проверки соединения с базой данных")
                return False
    except Exception as e:
        logger.error(f"Ошибка соединения с базой данных: {str(e)}")
        return False


def check_s3():
    """Проверяет соединение с S3"""
    logger.info("Проверка соединения с S3...")
    try:
        s3_service = S3Service(
            aws_access_key=settings.S3_AWS_ACCESS_KEY,
            aws_secret_key=settings.S3_AWS_SECRET_KEY,
            region=settings.S3_REGION,
            bucket=settings.S3_BUCKET,
            base_path=settings.S3_BASE_PATH
        )

        # Проверяем доступ к бакету
        buckets = s3_service.s3_client.list_buckets()
        bucket_exists = settings.S3_BUCKET in [bucket['Name'] for bucket in buckets['Buckets']]

        if bucket_exists:
            logger.info(f"Соединение с S3 установлено успешно. Бакет {settings.S3_BUCKET} существует")
            return True
        else:
            logger.warning(f"Соединение с S3 установлено, но бакет {settings.S3_BUCKET} не найден")
            return False
    except Exception as e:
        logger.error(f"Ошибка соединения с S3: {str(e)}")
        return False


def main():
    """Проверяет все соединения"""
    db_ok = check_database()
    s3_ok = check_s3()

    if db_ok and s3_ok:
        logger.info("Все соединения проверены успешно")
        sys.exit(0)
    else:
        logger.error("Проверка соединений завершилась с ошибками")
        sys.exit(1)


if __name__ == "__main__":
    main()