# api_gateway/repositories/customer_repository.py
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .base_repository import BaseRepository
from ..database.models import Customer


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: Session):
        super().__init__(Customer, session)

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