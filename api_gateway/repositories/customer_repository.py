from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from database.models import Customer, Appointment

from repositories.base_repository import BaseRepository
from database.models import Customer


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: Session):
        super().__init__(Customer, session)

    def count_all(self):
        """Подсчет общего количества клиентов"""
        try:
            return self.session.query(self.model_class).count()
        except Exception as e:
            print(f"Error counting customers: {str(e)}")
            raise

    def get_by_phone(self, phone: str) -> Optional[Customer]:
        return self.session.query(Customer).filter(Customer.phone == phone).first()

    def get_by_customer_id(self, customer_id: str) -> Optional[Customer]:
        return self.session.query(Customer).filter(Customer.customer_id == customer_id).first()

    def search_customers(self, query: str, limit: int = 20) -> List[Customer]:
        search = f"%{query}%"
        return self.session.query(Customer).filter(
            (Customer.name.ilike(search)) |
            (Customer.phone.ilike(search)) |
            (Customer.vehicle_make.ilike(search)) |
            (Customer.vehicle_model.ilike(search))
        ).limit(limit).all()

    def get_recent_customers(self, limit: int = 10) -> List[Customer]:
        return self.session.query(Customer).order_by(desc(Customer.last_visit)).limit(limit).all()

    def get_count_since(self, months_ago: int = 1) -> int:
        """
        Подсчет количества новых клиентов за указанный период
        """
        try:
            month_ago = datetime.utcnow() - timedelta(days=30 * months_ago)

            new_customers_count = self.session.query(func.count(Customer.id)).filter(
                Customer.created_at >= month_ago
            ).scalar()

            return new_customers_count
        except Exception as e:
            print(f"Error counting new customers: {str(e)}")
            return 0

    def get_count_with_visits(self, min_visits: int = 2) -> int:
        """
        Подсчет клиентов с определенным количеством визитов

        Args:
            min_visits (int): Минимальное количество визитов для клиента

        Returns:
            int: Количество клиентов с количеством визитов не менее min_visits
        """
        try:
            # Используем подзапрос для группировки и подсчета визитов клиентов
            repeat_customers_count = (
                    self.session.query(func.count(func.distinct(Customer.id)))
                    .join(Customer.appointments)  # Используем relationship для соединения таблиц
                    .group_by(Customer.id)
                    .having(func.count(Appointment.id) >= min_visits)
                    .scalar() or 0
            )

            return repeat_customers_count
        except Exception as e:
            print(f"Error counting repeat customers: {str(e)}")
            return 0