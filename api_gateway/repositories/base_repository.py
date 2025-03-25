# api_gateway/repositories/base_repository.py (обновленная версия)
from typing import Dict, List, Any, Optional, TypeVar, Generic, Type
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from database.postgresql import Base

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, model_class: Type[T], session: Session):
        self.model_class = model_class
        self.session = session

    def get_by_id(self, id: int) -> Optional[T]:
        try:
            return self.session.query(self.model_class).filter(self.model_class.id == id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model_class.__name__} by id: {str(e)}")
            raise

    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        try:
            return self.session.query(self.model_class).limit(limit).offset(offset).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting all {self.model_class.__name__}: {str(e)}")
            raise

    def create(self, data: Dict[str, Any]) -> T:
        try:
            # Фильтруем данные, чтобы избежать конфликтов с существующей схемой БД
            filtered_data = {
                k: v for k, v in data.items()
                if hasattr(self.model_class, k)
            }

            obj = self.model_class(**filtered_data)
            self.session.add(obj)
            self.session.flush()
            return obj
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model_class.__name__}: {str(e)}")
            raise

    def update(self, id: int, data: Dict[str, Any]) -> Optional[T]:
        try:
            obj = self.get_by_id(id)
            if obj:
                # Фильтруем данные, чтобы избежать конфликтов с существующей схемой БД
                for key, value in data.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                self.session.flush()
            return obj
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model_class.__name__}: {str(e)}")
            raise

    def delete(self, id: int) -> bool:
        try:
            obj = self.get_by_id(id)
            if obj:
                self.session.delete(obj)
                self.session.flush()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model_class.__name__}: {str(e)}")
            raise