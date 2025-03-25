# api_gateway/services/activity_service.py
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from repositories.activity_repository import ActivityRepository
from repositories.customer_repository import CustomerRepository


class ActivityService:
    def __init__(self, activity_repo: ActivityRepository, customer_repo: CustomerRepository):
        self.activity_repo = activity_repo
        self.customer_repo = customer_repo

    def get_recent_activity(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Получает последние активности"""
        with self.activity_repo.session_scope() as session:
            repo = ActivityRepository(session)
            activities = repo.get_recent(limit)

            return [self._format_activity(activity) for activity in activities]

    def get_customer_activity(self, customer_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Получает активности конкретного клиента"""
        with self.activity_repo.session_scope() as session:
            repo = ActivityRepository(session)

            # Получаем клиента по ID
            customer_repo = CustomerRepository(session)
            customer = customer_repo.get_by_customer_id(customer_id)
            if not customer:
                return []

            activities = repo.get_by_customer_id(customer.id, limit)

            return [self._format_activity(activity) for activity in activities]

    def log_activity(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Логирует новую активность"""
        with self.activity_repo.session_scope() as session:
            repo = ActivityRepository(session)

            # Если предоставлен customer_id, проверяем его существование
            customer_id = activity_data.get("customer_id")
            customer = None
            if customer_id:
                customer_repo = CustomerRepository(session)
                customer = customer_repo.get_by_customer_id(customer_id)
                if customer:
                    activity_data["customer_id"] = customer.id
                else:
                    activity_data["customer_id"] = None

            # Создаем запись активности
            activity = repo.create({
                "customer_id": activity_data.get("customer_id"),
                "message": activity_data.get("message", "Неизвестное действие"),
                "type": activity_data.get("type", "system"),
                "created_at": datetime.utcnow()
            })

            return {
                "id": activity.id,
                "type": activity.type
            }

    def _format_activity(self, activity) -> Dict[str, Any]:
        """Форматирует объект активности в словарь для API"""
        return {
            "id": str(activity.id),
            "message": activity.message,
            "type": activity.type,
            "created_at": activity.created_at.isoformat(),
            "customer": {
                "id": activity.customer.customer_id if activity.customer else None,
                "name": activity.customer.name if activity.customer else None
            }
        }