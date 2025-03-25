# api_gateway/repositories/activity_repository.py
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from repositories.base_repository import BaseRepository
from database.models import Activity


class ActivityRepository(BaseRepository[Activity]):
    def __init__(self, session: Session):
        super().__init__(Activity, session)

    def get_recent(self, limit: int = 10) -> List[Activity]:
        """Получает последние активности"""
        return self.session.query(Activity) \
            .order_by(desc(Activity.created_at)) \
            .limit(limit) \
            .all()

    def get_by_customer_id(self, customer_id: int, limit: int = 20) -> List[Activity]:
        """Получает активности конкретного клиента"""
        return self.session.query(Activity) \
            .filter(Activity.customer_id == customer_id) \
            .order_by(desc(Activity.created_at)) \
            .limit(limit) \
            .all()

    def log_activity(self, customer_id: Optional[int], message: str, type: str) -> Activity:
        """Добавляет новую запись активности"""
        activity = Activity(
            customer_id=customer_id,
            message=message,
            type=type
        )
        self.session.add(activity)
        self.session.flush()
        return activity