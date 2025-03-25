# api_gateway/repositories/service_repository.py
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from repositories.base_repository import BaseRepository
from database.models import Service


class ServiceRepository(BaseRepository[Service]):
    def __init__(self, session: Session):
        super().__init__(Service, session)

    def get_by_service_id(self, service_id: str) -> Optional[Service]:
        """Получает услугу по уникальному ID"""
        return self.session.query(Service).filter(Service.service_id == service_id).first()

    def get_active_services(self) -> List[Service]:
        """Получает список активных услуг"""
        return self.session.query(Service).filter(Service.active == True).all()

    def get_by_category(self, category: str) -> List[Service]:
        """Получает услуги по категории"""
        return self.session.query(Service) \
            .filter(Service.category == category) \
            .filter(Service.active == True) \
            .all()