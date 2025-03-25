# api_gateway/database/init_data.py
import logging
from sqlalchemy.exc import SQLAlchemyError
from database.models import User

logger = logging.getLogger(__name__)


def initialize_default_data(db_service):
    """
    Инициализирует только базовые данные для нормальной работы системы.
    Не создает данные о ценах и услугах, так как они должны быть загружены пользователем.
    """
    logger.info("Проверка наличия базовых данных...")

    try:
        with db_service.session_scope() as session:
            # Проверяем, есть ли пользователи-администраторы
            admin_count = session.query(User).filter(User.role == "admin").count()
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
                logger.info("Пользователь-администратор по умолчанию создан")

            # Здесь можно добавить другую инициализацию, если необходимо
            # Но без создания услуг и цен, так как они должны загружаться пользователем

        logger.info("Инициализация базовых данных завершена")
        return True

    except SQLAlchemyError as e:
        logger.error(f"Ошибка инициализации базовых данных: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при инициализации данных: {str(e)}")
        return False