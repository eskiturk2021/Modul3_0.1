# api_gateway/database/init_data.py
import logging
import traceback
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from database.models import User

logger = logging.getLogger(__name__)


def initialize_default_data(db_service):
    """
    Инициализирует только базовые данные для нормальной работы системы.
    Не создает данные о ценах и услугах, так как они должны быть загружены пользователем.
    """
    logger.info("Проверка наличия базовых данных...")

    try:
        # Проверяем соединение с базой данных
        logger.info("Проверка соединения с базой данных перед инициализацией данных...")
        with db_service.session_scope() as session:
            try:
                # Используем text() для текстовых SQL-запросов
                result = session.execute(text("SELECT 1")).scalar()
                if result == 1:
                    logger.info("Соединение с базой данных успешно")
                else:
                    logger.warning(f"Странный результат проверки соединения: {result}")
            except Exception as conn_e:
                logger.error(f"Ошибка при проверке соединения: {str(conn_e)}")
                logger.error(traceback.format_exc())
                raise

        with db_service.session_scope() as session:
            # Проверяем, есть ли пользователи-администраторы
            logger.info("Проверка наличия пользователей-администраторов...")
            admin_count = session.query(User).filter(User.role == "admin").count()
            logger.info(f"Найдено {admin_count} администраторов")

            if admin_count == 0:
                logger.info("Создание пользователя-администратора по умолчанию...")
                # Хешированный пароль 'admin123'
                default_password = "9d4e1e23bd5b727046a9e3b4b7db57bd8d6ee684"  # SHA-1 хеш
                admin_user = User(
                    username="admin",
                    email="admin@example.com",
                    password=default_password,
                    role="admin"
                )
                session.add(admin_user)
                logger.info("Пользователь-администратор по умолчанию добавлен в сессию")

                # Проверка добавления перед коммитом
                session.flush()
                logger.info(f"Пользователь-администратор создан с ID: {admin_user.id}")

            # Проверяем общее количество пользователей после инициализации
            total_users = session.query(User).count()
            logger.info(f"Общее количество пользователей в системе: {total_users}")

            # Здесь можно добавить другую инициализацию, если необходимо
            # Но без создания услуг и цен, так как они должны загружаться пользователем

        logger.info("Инициализация базовых данных завершена")
        return True

    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при инициализации базовых данных: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при инициализации данных: {str(e)}")
        logger.error(traceback.format_exc())
        return False