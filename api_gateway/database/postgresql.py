# api_gateway/database/postgresql.py
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()


class DatabaseService:
    def __init__(self, connection_string: str):
        self.engine = sa.create_engine(
            connection_string,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800
        )
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)

    @contextmanager
    def session_scope(self):
        """Обеспечивает контекст транзакции"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            session.rollback()
            raise e
        finally:
            session.close()

    def check_tables(self):
        """Проверяет наличие необходимых таблиц в базе данных"""
        insp = sa.inspect(self.engine)
        existing_tables = insp.get_table_names()
        required_tables = ['user_submissions', 'customers', 'messages', 'appointments', 'available_slots']

        missing_tables = [table for table in required_tables if table not in existing_tables]

        if missing_tables:
            logger.warning(f"Missing required tables: {', '.join(missing_tables)}")
            return False
        return True