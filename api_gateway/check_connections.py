# api_gateway/check_connections.py
import os
import sys
import logging
import traceback
from sqlalchemy import text
from database.postgresql import DatabaseService
from storage.s3_client import S3Service
from config import settings

# Настройка более подробного логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('connection_check.log')  # Сохраняем логи в файл для анализа
    ]
)
logger = logging.getLogger(__name__)


def check_database():
    """Проверяет соединение с базой данных PostgreSQL"""
    logger.info("Проверка соединения с базой данных...")
    logger.info(
        f"Используется строка подключения: {settings.DATABASE_URL.replace(':'.join(settings.DATABASE_URL.split(':')[2:]), '***')}")

    try:
        db_service = DatabaseService(settings.DATABASE_URL)
        logger.info("Экземпляр DatabaseService создан успешно")

        with db_service.session_scope() as session:
            logger.info("Сессия открыта успешно, выполнение запроса SELECT 1")
            # Используем text() для текстовых SQL-запросов
            result = session.execute(text("SELECT 1")).scalar()

            if result == 1:
                logger.info("Соединение с базой данных установлено успешно")
                return True
            else:
                logger.error(f"Ошибка проверки соединения с базой данных: результат {result} вместо 1")
                return False
    except Exception as e:
        logger.error(f"Ошибка соединения с базой данных: {str(e)}")
        logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
        return False


def check_s3():
    """Проверяет соединение с S3"""
    logger.info("Проверка соединения с S3...")
    logger.info(
        f"Используются параметры: регион={settings.S3_REGION}, бакет={settings.S3_BUCKET}, путь={settings.S3_BASE_PATH}")

    try:
        logger.info("Создание экземпляра S3Service...")
        s3_service = S3Service(
            aws_access_key=settings.S3_AWS_ACCESS_KEY,
            aws_secret_key=settings.S3_AWS_SECRET_KEY,
            region=settings.S3_REGION,
            bucket=settings.S3_BUCKET,
            base_path=settings.S3_BASE_PATH
        )
        logger.info("Экземпляр S3Service создан успешно")

        # Проверяем доступ к бакету
        logger.info("Выполнение list_buckets для проверки доступа...")
        buckets = s3_service.s3_client.list_buckets()
        logger.info(f"list_buckets выполнен успешно, получено {len(buckets.get('Buckets', []))} бакетов")

        bucket_names = [bucket['Name'] for bucket in buckets['Buckets']]
        logger.info(f"Найденные бакеты: {', '.join(bucket_names)}")

        bucket_exists = settings.S3_BUCKET in bucket_names

        if bucket_exists:
            logger.info(f"Соединение с S3 установлено успешно. Бакет {settings.S3_BUCKET} существует")
            return True
        else:
            logger.warning(
                f"Соединение с S3 установлено, но бакет {settings.S3_BUCKET} не найден. Доступные бакеты: {', '.join(bucket_names)}")
            return False
    except Exception as e:
        logger.error(f"Ошибка соединения с S3: {str(e)}")
        logger.error(f"Трассировка ошибки: {traceback.format_exc()}")

        # Проверяем доступность учетных данных
        if not settings.S3_AWS_ACCESS_KEY or settings.S3_AWS_ACCESS_KEY == "dummy-access-key":
            logger.error("S3_AWS_ACCESS_KEY не установлен или имеет значение по умолчанию")
        if not settings.S3_AWS_SECRET_KEY or settings.S3_AWS_SECRET_KEY == "dummy-secret-key":
            logger.error("S3_AWS_SECRET_KEY не установлен или имеет значение по умолчанию")

        return False


def main():
    """Проверяет все соединения"""
    logger.info("=== Начало проверки соединений ===")
    logger.info(
        f"Запущен с переменными окружения: PORT={os.getenv('PORT')}, DATABASE_URL={settings.DATABASE_URL.replace(':'.join(settings.DATABASE_URL.split(':')[2:]), '***')}")

    db_ok = check_database()
    logger.info(f"Результат проверки БД: {'успешно' if db_ok else 'не успешно'}")

    s3_ok = check_s3()
    logger.info(f"Результат проверки S3: {'успешно' if s3_ok else 'не успешно'}")

    if db_ok and s3_ok:
        logger.info("Все соединения проверены успешно")
        sys.exit(0)
    else:
        logger.error("Проверка соединений завершилась с ошибками")
        if not db_ok:
            logger.error("Не удалось подключиться к базе данных PostgreSQL")
        if not s3_ok:
            logger.error("Не удалось подключиться к хранилищу S3")
        sys.exit(1)


if __name__ == "__main__":
    main()