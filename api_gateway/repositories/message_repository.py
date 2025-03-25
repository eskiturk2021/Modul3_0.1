# api_gateway/repositories/message_repository.py
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime

from repositories.base_repository import BaseRepository
from database.models import Message


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: Session):
        super().__init__(Message, session)

    def get_messages_by_phone(self, phone: str, limit: int = 50, offset: int = 0) -> List[Message]:
        """Получает историю сообщений по номеру телефона"""
        return self.session.query(Message) \
            .filter(Message.phone == phone) \
            .order_by(desc(Message.created_at)) \
            .limit(limit) \
            .offset(offset) \
            .all()

    def get_messages_by_thread(self, thread_id: str, limit: int = 50, offset: int = 0) -> List[Message]:
        """Получает сообщения по ID цепочки"""
        return self.session.query(Message) \
            .filter(Message.thread_id == thread_id) \
            .order_by(Message.created_at) \
            .limit(limit) \
            .offset(offset) \
            .all()

    def get_recent_messages(self, limit: int = 20) -> List[Message]:
        """Получает последние сообщения по всем клиентам"""
        return self.session.query(Message) \
            .order_by(desc(Message.created_at)) \
            .limit(limit) \
            .all()

    def add_message(self, message_data: Dict[str, Any]) -> Message:
        """Добавляет новое сообщение"""
        message = Message(**message_data)
        self.session.add(message)
        self.session.flush()
        return message

    def get_unique_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получает список уникальных диалогов (по одному последнему сообщению для каждого телефона)"""
        # Здесь используем подзапрос для получения последнего сообщения для каждого телефона
        # Это сложный запрос, который в SQLAlchemy может быть реализован по-разному
        # в зависимости от версии и диалекта SQL

        # Простая реализация - не самая эффективная, но работает для небольших объемов
        from sqlalchemy import func

        # Находим максимальную дату сообщения для каждого телефона
        subq = self.session.query(
            Message.phone,
            func.max(Message.created_at).label('max_date')
        ).group_by(Message.phone).subquery()

        # Присоединяем основную таблицу к подзапросу
        messages = self.session.query(Message) \
            .join(subq, and_(
            Message.phone == subq.c.phone,
            Message.created_at == subq.c.max_date
        )) \
            .order_by(desc(Message.created_at)) \
            .limit(limit) \
            .all()

        return [
            {
                'phone': msg.phone,
                'message_type': msg.message_type,
                'message_text': msg.message_text,
                'thread_id': msg.thread_id,
                'created_at': msg.created_at
            } for msg in messages
        ]