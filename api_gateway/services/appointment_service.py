# api_gateway/services/appointment_service.py
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, date, time, timedelta

from repositories.appointment_repository import AppointmentRepository
from repositories.customer_repository import CustomerRepository
from repositories.available_slot_repository import AvailableSlotRepository
from services.websocket_service import websocket_service
import asyncio

class AppointmentService:
    def __init__(self, appointment_repo: AppointmentRepository, customer_repo: CustomerRepository,
                 slot_repo: AvailableSlotRepository):
        self.appointment_repo = appointment_repo
        self.customer_repo = customer_repo
        self.slot_repo = slot_repo

    def get_upcoming_appointments(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Получает предстоящие записи на обслуживание"""
        with self.appointment_repo.session_scope() as session:
            appointment_repo = AppointmentRepository(session)

            # Получаем записи, где дата >= сегодняшней
            appointments = appointment_repo.get_upcoming_appointments(limit, offset)

            return [
                {
                    "id": app.appointment_id,
                    "customer": {
                        "name": app.customer_name,
                        "phone": app.customer_phone
                    },
                    "service": {
                        "name": app.service_type
                    },
                    "appointment_date": app.appointment_date.isoformat(),
                    "appointment_time": app.appointment_time.isoformat(),
                    "status": app.status,
                    "estimated_cost": float(app.estimated_cost) if app.estimated_cost else None
                } for app in appointments
            ]

    def get_appointment_by_id(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о конкретной записи"""
        with self.appointment_repo.session_scope() as session:
            appointment_repo = AppointmentRepository(session)

            appointment = appointment_repo.get_by_appointment_id(appointment_id)
            if not appointment:
                return None

            return {
                "id": appointment.appointment_id,
                "customer": {
                    "id": appointment.customer_phone,  # Используем телефон как ID
                    "name": appointment.customer_name,
                    "phone": appointment.customer_phone
                },
                "vehicle": {
                    "make": appointment.vehicle_make,
                    "model": appointment.vehicle_model,
                    "year": appointment.vehicle_year
                },
                "service": {
                    "type": appointment.service_type
                },
                "appointment_date": appointment.appointment_date.isoformat(),
                "appointment_time": appointment.appointment_time.isoformat(),
                "estimated_cost": float(appointment.estimated_cost) if appointment.estimated_cost else None,
                "status": appointment.status,
                "created_at": appointment.created_at.isoformat()
            }

    def create_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новую запись на обслуживание"""
        with self.appointment_repo.session_scope() as session:
            appointment_repo = AppointmentRepository(session)
            customer_repo = CustomerRepository(session)
            slot_repo = AvailableSlotRepository(session)

            # Проверяем, существует ли клиент
            customer = customer_repo.get_by_customer_id(appointment_data.get("customer_id"))
            if not customer:
                raise ValueError("Клиент не найден")

            # Проверяем доступность слота
            appointment_date = appointment_data.get("appointment_date")
            appointment_time = appointment_data.get("appointment_time")

            # Конвертируем строки в datetime объекты, если нужно
            if isinstance(appointment_date, str):
                appointment_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
            if isinstance(appointment_time, str):
                appointment_time = datetime.strptime(appointment_time, "%H:%M").time()

            # Проверяем, что дата не в прошлом
            if appointment_date < date.today():
                raise ValueError("Нельзя создать запись на прошедшую дату")

            # Проверяем доступность слота
            slot = slot_repo.get_slot(appointment_date, appointment_time)
            if slot and not slot.is_available:
                raise ValueError("Выбранное время уже занято")

            # Создаем уникальный ID для записи
            appointment_id = f"APT-{uuid.uuid4().hex[:8].upper()}"

            # Получаем дополнительные данные клиента
            customer_name = customer.name
            customer_phone = customer.phone

            # Создаем запись
            new_appointment = appointment_repo.create({
                "appointment_id": appointment_id,
                "customer_phone": customer_phone,
                "customer_name": customer_name,
                "vehicle_make": customer.vehicle_make,
                "vehicle_model": customer.vehicle_model,
                "vehicle_year": customer.vehicle_year,
                "service_type": appointment_data.get("service_type"),
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "estimated_cost": appointment_data.get("estimated_cost"),
                "status": "pending",
                "created_at": datetime.utcnow()
            })

            # Обновляем доступность слота
            if slot:
                slot_repo.update(slot.id, {"is_available": False})
            else:
                slot_repo.create({
                    "date": appointment_date,
                    "time": appointment_time,
                    "is_available": False
                })

            # Обновляем данные клиента (последний визит)
            customer_repo.update(customer.id, {
                "last_visit": datetime.combine(appointment_date, appointment_time),
                "total_visits": customer.total_visits + 1
            })

            appointment_data = {
                "id": appointment_id,
                "customer": {
                    "name": customer_name,
                    "phone": customer_phone
                },
                "service": {
                    "type": appointment_data.get("service_type")
                },
                "appointment_date": appointment_date.isoformat() if hasattr(appointment_date, "isoformat") else str(appointment_date),

                "appointment_time": appointment_time.isoformat() if hasattr(appointment_time, "isoformat") else str(appointment_time),

                "status": "pending"
            }

            # Запускаем корутину в фоновом режиме
            asyncio.create_task(websocket_service.emit_appointment_created(appointment_data))

            return {
                "id": appointment_id,
                "status": "created"
            }



    def update_appointment(self, appointment_id: str, appointment_data: Dict[str, Any]) -> bool:
        """Обновляет информацию о записи"""
        with self.appointment_repo.session_scope() as session:
            appointment_repo = AppointmentRepository(session)
            slot_repo = AvailableSlotRepository(session)

            # Получаем существующую запись
            appointment = appointment_repo.get_by_appointment_id(appointment_id)
            if not appointment:
                return False

            # Если меняется время, проверяем доступность нового слота
            if "appointment_date" in appointment_data or "appointment_time" in appointment_data:
                new_date = appointment_data.get("appointment_date", appointment.appointment_date)
                new_time = appointment_data.get("appointment_time", appointment.appointment_time)

                # Конвертируем строки в datetime объекты, если нужно
                if isinstance(new_date, str):
                    new_date = datetime.strptime(new_date, "%Y-%m-%d").date()
                if isinstance(new_time, str):
                    new_time = datetime.strptime(new_time, "%H:%M").time()

                # Проверяем, что дата не в прошлом
                if new_date < date.today():
                    raise ValueError("Нельзя обновить запись на прошедшую дату")

                # Если дата или время изменились, проверяем доступность нового слота
                if new_date != appointment.appointment_date or new_time != appointment.appointment_time:
                    new_slot = slot_repo.get_slot(new_date, new_time)
                    if new_slot and not new_slot.is_available:
                        raise ValueError("Выбранное время уже занято")

                    # Освобождаем старый слот
                    old_slot = slot_repo.get_slot(appointment.appointment_date, appointment.appointment_time)
                    if old_slot:
                        slot_repo.update(old_slot.id, {"is_available": True})

                    # Занимаем новый слот
                    if new_slot:
                        slot_repo.update(new_slot.id, {"is_available": False})
                    else:
                        slot_repo.create({
                            "date": new_date,
                            "time": new_time,
                            "is_available": False
                        })

            # Обновляем запись
            update_data = appointment_data.copy()
            if "appointment_date" in update_data and isinstance(update_data["appointment_date"], str):
                update_data["appointment_date"] = datetime.strptime(update_data["appointment_date"], "%Y-%m-%d").date()
            if "appointment_time" in update_data and isinstance(update_data["appointment_time"], str):
                update_data["appointment_time"] = datetime.strptime(update_data["appointment_time"], "%H:%M").time()

            appointment_repo.update(appointment.id, update_data)

            # Отправляем событие WebSocket
            ws_data = {
                "id": appointment_id,
                "status": update_data.get("status", "updated"),
                "changes": appointment_data
            }

            # Запускаем корутину в фоновом режиме
            asyncio.create_task(websocket_service.emit_appointment_updated(ws_data))

            return True

    def cancel_appointment(self, appointment_id: str) -> bool:
        """Отменяет запись"""
        with self.appointment_repo.session_scope() as session:
            appointment_repo = AppointmentRepository(session)
            slot_repo = AvailableSlotRepository(session)

            # Получаем существующую запись
            appointment = appointment_repo.get_by_appointment_id(appointment_id)
            if not appointment:
                return False

            # Обновляем статус записи
            appointment_repo.update(appointment.id, {"status": "cancelled"})

            # Освобождаем слот
            slot = slot_repo.get_slot(appointment.appointment_date, appointment.appointment_time)
            if slot:
                slot_repo.update(slot.id, {"is_available": True})

            return True

    def get_calendar_appointments(self, year: int, month: int) -> List[Dict[str, Any]]:
        """Получает записи для календаря на указанный месяц"""
        with self.appointment_repo.session_scope() as session:
            appointment_repo = AppointmentRepository(session)

            # Определяем начало и конец месяца
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)

            # Получаем записи за месяц
            appointments = appointment_repo.get_appointments_in_range(start_date, end_date)

            return [
                {
                    "id": app.appointment_id,
                    "title": f"{app.service_type} - {app.customer_name}",
                    "start": f"{app.appointment_date.isoformat()}T{app.appointment_time.isoformat()}",
                    "end": self._calculate_end_time(app.appointment_date, app.appointment_time, duration_minutes=60),
                    "customer": {
                        "id": app.customer_phone,
                        "name": app.customer_name
                    },
                    "service": {
                        "type": app.service_type
                    },
                    "status": app.status
                } for app in appointments
            ]

    def get_available_slots(self, target_date: date) -> List[Dict[str, Any]]:
        """Получает доступные слоты для записи на указанную дату"""
        with self.slot_repo.session_scope() as session:
            slot_repo = AvailableSlotRepository(session)

            # Получаем все слоты на указанную дату
            all_slots = slot_repo.get_slots_for_date(target_date)

            # Формируем рабочие часы (с 8:00 до 18:00 с шагом 30 минут)
            working_hours = []
            for hour in range(8, 18):
                for minute in [0, 30]:
                    slot_time = time(hour, minute)

                    # Проверяем, занят ли слот
                    slot = next((s for s in all_slots if s.time == slot_time), None)
                    is_available = not slot or slot.is_available

                    working_hours.append({
                        "time": slot_time.strftime("%H:%M"),
                        "is_available": is_available
                    })

            return working_hours

    def _calculate_end_time(self, date_obj: date, time_obj: time, duration_minutes: int) -> str:
        """Рассчитывает время окончания по времени начала и длительности"""
        start_datetime = datetime.combine(date_obj, time_obj)
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)

        return end_datetime.isoformat()