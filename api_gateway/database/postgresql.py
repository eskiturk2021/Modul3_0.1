# api_gateway/database/postgresql.py
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import logging
import traceback
from config import settings

logger = logging.getLogger(__name__)
Base = declarative_base()


class DatabaseService:
    def __init__(self, connection_string: str):
        logger.info(
            f"Инициализация DatabaseService с параметрами: connection_string={connection_string.replace(':'.join(connection_string.split(':')[2:]), '***')}")

        # Оптимизированные настройки для продакшена
        try:
            logger.info(
                f"Настройка параметров подключения: pool_size={settings.DB_POOL_SIZE}, max_overflow={settings.DB_MAX_OVERFLOW}, pool_timeout={settings.DB_POOL_TIMEOUT}")
            self.engine = sa.create_engine(
                connection_string,
                pool_pre_ping=True,  # Проверяет соединение перед использованием
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
                echo=settings.DEBUG,  # SQL запросы логируются только в режиме отладки
                connect_args={"options": "-c timezone=utc"}  # Устанавливаем UTC для всех соединений
            )
            logger.info("SQLAlchemy engine создан успешно")

            session_factory = sessionmaker(bind=self.engine)
            self.Session = scoped_session(session_factory)
            logger.info("Session factory настроена успешно")

            # Проверяем соединение сразу после создания
            try:
                with self.session_scope() as session:
                    result = session.execute("SELECT 1").scalar()
                    if result == 1:
                        logger.info("Тестовое соединение с базой данных успешно")
                    else:
                        logger.warning("Странный результат тестового соединения с базой данных")
            except Exception as test_e:
                logger.warning(f"Тестовое соединение с базой данных не удалось: {str(test_e)}")

        except Exception as e:
            logger.error(f"Ошибка при инициализации DatabaseService: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    @contextmanager
    def session_scope(self):
        """Обеспечивает контекст транзакции"""
        session = self.Session()
        logger.debug("Открыта новая сессия базы данных")
        try:
            yield session
            session.commit()
            logger.debug("Сессия успешно закоммичена")
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            logger.error(traceback.format_exc())
            session.rollback()
            logger.debug("Выполнен откат сессии после ошибки")
            raise e
        finally:
            session.close()
            logger.debug("Сессия закрыта")

    def check_tables(self):
        """Проверяет наличие необходимых таблиц в базе данных"""
        logger.info("Проверка наличия таблиц в базе данных...")
        try:
            insp = sa.inspect(self.engine)
            existing_tables = insp.get_table_names()
            logger.info(f"Найдены таблицы: {', '.join(existing_tables)}")

            required_tables = ['user_submissions', 'customers', 'messages', 'appointments', 'available_slots',
                               'users', 'services', 'documents', 'activities', 'conversations']
            logger.info(f"Требуемые таблицы: {', '.join(required_tables)}")

            missing_tables = [table for table in required_tables if table not in existing_tables]

            if missing_tables:
                logger.warning(f"Отсутствуют требуемые таблицы: {', '.join(missing_tables)}")
                return False

            logger.info("Все требуемые таблицы найдены")
            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке таблиц: {str(e)}")
            logger.error(traceback.format_exc())
            return False


# Инициализация сервиса базы данных
try:
    logger.info(
        f"Создание экземпляра db_service с DATABASE_URL={settings.DATABASE_URL.replace(':'.join(settings.DATABASE_URL.split(':')[2:]), '***')}")
    db_service = DatabaseService(settings.DATABASE_URL)
    logger.info("Экземпляр db_service успешно создан")
except Exception as e:
    logger.critical(f"Не удалось создать экземпляр db_service: {str(e)}")
    logger.critical(traceback.format_exc())