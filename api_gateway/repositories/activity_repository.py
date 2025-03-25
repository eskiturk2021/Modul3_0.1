# api_gateway/repositories/activity_repository.py
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from repositories.base_repository import BaseRepository
from database.models import Activity


class ActivityRepository(BaseRepository[Activity]):
    def __init__(self, session: Session):
        super().__init__(Activity, session)

    def get_recent(self, limit: int = 10) -> List[Activity]:
        return self.session.query(Activity) \
            .order_by(desc(Activity.created_at)) \
            .limit(limit) \
            .all()

    def get_by_customer_id(self, customer_id: str, limit: int = 20) -> List[Activity]:
        return self.session.query(Activity) \
            .filter(Activity.customer_id == customer_id) \
            .order_by(desc(Activity.created_at)) \
            .limit(limit) \
            .all()