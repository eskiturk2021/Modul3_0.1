# api_gateway/repositories/appointment_repository.py
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import date, time

from repositories.base_repository import BaseRepository
from database.models import Appointment


class AppointmentRepository(BaseRepository[Appointment]):
    def __init__(self, session: Session):
        super().__init__(Appointment, session)

    def get_by_appointment_id(self, appointment_id: str) -> Optional[Appointment]:
        """Получает запись по уникальному ID записи"""
        return self.session.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()

    def get_by_customer_phone(self, phone: str, limit: int = 10) -> List[Appointment]:
        """Получает список записей для клиента по номеру телефона"""
        return self.session.query(Appointment) \
            .filter(Appointment.customer_phone == phone) \
            .order_by(desc(Appointment.appointment_date), desc(Appointment.appointment_time)) \
            .limit(limit) \
            .all()

    def get_upcoming_appointments(self, limit: int = 10, offset: int = 0) -> List[Appointment]:
        """Получает список предстоящих записей"""
        today = date.today()
        return self.session.query(Appointment) \
            .filter(and_(
            Appointment.appointment_date >= today,
            Appointment.status.in_(['pending', 'confirmed'])
        )) \
            .order_by(Appointment.appointment_date, Appointment.appointment_time) \
            .limit(limit) \
            .offset(offset) \
            .all()

    def get_calendar_appointments(self, year: int, month: int) -> List[Appointment]:
        """Получает записи для календаря на указанный месяц"""
        start_date = date(year, month, 1)
        # Определяем конец месяца
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        return self.session.query(Appointment) \
            .filter(and_(
            Appointment.appointment_date >= start_date,
            Appointment.appointment_date < end_date
        )) \
            .order_by(Appointment.appointment_date, Appointment.appointment_time) \
            .all()

    def check_slot_availability(self, appointment_date: date, appointment_time: time) -> bool:
        """Проверяет, доступен ли указанный временной слот"""
        count = self.session.query(Appointment) \
            .filter(and_(
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.status.in_(['pending', 'confirmed'])
        )) \
            .count()

        return count == 0

    def create_appointment(self, appointment_data: Dict[str, Any]) -> Appointment:
        """Создает новую запись"""
        appointment = Appointment(**appointment_data)
        self.session.add(appointment)
        self.session.flush()
        return appointment

    def update_appointment_status(self, appointment_id: str, status: str) -> bool:
        """Обновляет статус записи"""
        appointment = self.get_by_appointment_id(appointment_id)
        if appointment:
            appointment.status = status
            self.session.flush()
            return True
        return False

    def cancel_appointment(self, appointment_id: str) -> bool:
        """Отменяет запись"""
        return self.update_appointment_status(appointment_id, 'cancelled')

    def confirm_appointment(self, appointment_id: str) -> bool:
        """Подтверждает запись"""
        return self.update_appointment_status(appointment_id, 'confirmed')

    def complete_appointment(self, appointment_id: str) -> bool:
        """Отмечает запись как выполненную"""
        return self.update_appointment_status(appointment_id, 'completed')