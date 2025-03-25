# api_gateway/services/customer_service.py
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from repositories.customer_repository import CustomerRepository
from repositories.appointment_repository import AppointmentRepository
from repositories.message_repository import MessageRepository


class CustomerService:
    def __init__(self, customer_repo: CustomerRepository, appointment_repo: AppointmentRepository,
                 message_repo: MessageRepository):
        self.customer_repo = customer_repo
        self.appointment_repo = appointment_repo
        self.message_repo = message_repo

    def get_customer_by_id(self, customer_id: str) -> Dict:
        """Получает информацию о клиенте по ID"""
        with self.customer_repo.session_scope() as session:
            customer_repo = CustomerRepository(session)
            appointment_repo = AppointmentRepository(session)

            customer = customer_repo.get_by_customer_id(customer_id)
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")

            # Получаем последние записи
            appointments = appointment_repo.get_by_customer_phone(customer.phone, limit=5)

            return {
                'id': customer.customer_id,
                'name': customer.name,
                'phone': customer.phone,
                'vehicle': {
                    'make': customer.vehicle_make,
                    'model': customer.vehicle_model,
                    'year': customer.vehicle_year
                },
                'last_visit': customer.last_visit.isoformat() if customer.last_visit else None,
                'total_visits': customer.total_visits,
                'recent_appointments': [
                    {
                        'id': app.appointment_id,
                        'date': app.appointment_date.isoformat(),
                        'time': app.appointment_time.isoformat(),
                        'service_type': app.service_type,
                        'status': app.status
                    } for app in appointments
                ]
            }

    def get_customers(self, search: Optional[str] = None, limit: int = 20, offset: int = 0) -> Dict:
        """Получает список клиентов с фильтрацией"""
        with self.customer_repo.session_scope() as session:
            customer_repo = CustomerRepository(session)

            if search:
                customers = customer_repo.search_customers(search, limit)
                total = len(customers)  # В реальном приложении нужно отдельно считать общее количество
            else:
                customers = customer_repo.get_all(limit, offset)
                total = session.query(self.customer_repo.model_class).count()

            return {
                'customers': [
                    {
                        'id': c.customer_id,
                        'name': c.name,
                        'phone': c.phone,
                        'vehicle_make': c.vehicle_make,
                        'vehicle_model': c.vehicle_model,
                        'last_visit': c.last_visit.isoformat() if c.last_visit else None
                    } for c in customers
                ],
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
            }

    def create_customer(self, customer_data: Dict) -> Dict:
        """Создает нового клиента"""
        with self.customer_repo.session_scope() as session:
            customer_repo = CustomerRepository(session)

            # Проверяем, существует ли клиент с таким телефоном
            existing = customer_repo.get_by_phone(customer_data.get('phone'))
            if existing:
                return {
                    'id': existing.customer_id,
                    'status': 'exists',
                    'message': 'Customer with this phone already exists'
                }

            # Создаем уникальный ID клиента
            customer_id = f"CUST-{uuid.uuid4().hex[:8].upper()}"

            # Создаем клиента
            new_customer = customer_repo.create({
                'customer_id': customer_id,
                'phone': customer_data.get('phone'),
                'name': customer_data.get('name'),
                'vehicle_make': customer_data.get('vehicle_make'),
                'vehicle_model': customer_data.get('vehicle_model'),
                'vehicle_year': customer_data.get('vehicle_year'),
                'created_at': datetime.utcnow()
            })

            return {
                'id': new_customer.customer_id,
                'status': 'created',
                'message': 'Customer created successfully'
            }