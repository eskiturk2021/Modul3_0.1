# api_gateway/repositories/available_slot_repository.py
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, time, datetime, timedelta

from repositories.base_repository import BaseRepository
from database.models import AvailableSlot


class AvailableSlotRepository(BaseRepository[AvailableSlot]):
    def __init__(self, session: Session):
        super().__init__(AvailableSlot, session)

    def get_slots_by_date(self, slot_date: date) -> List[AvailableSlot]:
        """Получает все слоты на указанную дату"""
        return self.session.query(AvailableSlot) \
            .filter(AvailableSlot.date == slot_date) \
            .order_by(AvailableSlot.time) \
            .all()

    def get_available_slots_by_date(self, slot_date: date) -> List[AvailableSlot]:
        """Получает доступные слоты на указанную дату"""
        return self.session.query(AvailableSlot) \
            .filter(and_(
            AvailableSlot.date == slot_date,
            AvailableSlot.is_available == True
        )) \
            .order_by(AvailableSlot.time) \
            .all()

    def get_available_slots_range(self, start_date: date, end_date: date) -> Dict[str, List[str]]:
        """Получает доступные слоты для диапазона дат"""
        slots = self.session.query(AvailableSlot) \
            .filter(and_(
            AvailableSlot.date >= start_date,
            AvailableSlot.date <= end_date,
            AvailableSlot.is_available == True
        )) \
            .order_by(AvailableSlot.date, AvailableSlot.time) \
            .all()

        # Группировка по датам
        result = {}
        for slot in slots:
            date_str = slot.date.isoformat()
            if date_str not in result:
                result[date_str] = []

            result[date_str].append(slot.time.strftime('%H:%M'))

        return result

    def update_slot_availability(self, slot_date: date, slot_time: time, is_available: bool) -> bool:
        """Обновляет доступность слота"""
        slot = self.session.query(AvailableSlot) \
            .filter(and_(
            AvailableSlot.date == slot_date,
            AvailableSlot.time == slot_time
        )) \
            .first()

        if slot:
            slot.is_available = is_available
            self.session.flush()
            return True
        else:
            # Если слот не существует, создаем его
            new_slot = AvailableSlot(
                date=slot_date,
                time=slot_time,
                is_available=is_available
            )
            self.session.add(new_slot)
            self.session.flush()
            return True

    def generate_slots_for_date(self, slot_date: date, start_hour: int = 8, end_hour: int = 18,
                                interval_minutes: int = 30) -> List[AvailableSlot]:
        """Генерирует временные слоты для указанной даты"""
        slots = []
        current_time = datetime.combine(slot_date, time(start_hour, 0))
        end_time = datetime.combine(slot_date, time(end_hour, 0))

        while current_time < end_time:
            slot_time = current_time.time()

            # Проверяем, существует ли уже такой слот
            existing_slot = self.session.query(AvailableSlot) \
                .filter(and_(
                AvailableSlot.date == slot_date,
                AvailableSlot.time == slot_time
            )) \
                .first()

            if existing_slot:
                slots.append(existing_slot)
            else:
                # Создаем новый слот
                new_slot = AvailableSlot(
                    date=slot_date,
                    time=slot_time,
                    is_available=True
                )
                self.session.add(new_slot)
                slots.append(new_slot)

            # Увеличиваем время на интервал
            current_time += timedelta(minutes=interval_minutes)

        self.session.flush()
        return slots