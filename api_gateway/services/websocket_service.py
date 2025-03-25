# api_gateway/services/websocket_service.py
import socketio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WebSocketService:
    def __init__(self):
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins='*'  # Для продакшена используйте конкретные домены
        )
        self.app = socketio.ASGIApp(self.sio)
        self._setup_handlers()
        logger.info("WebSocket service initialized")

    def _setup_handlers(self):
        @self.sio.event
        async def connect(sid, environ):
            logger.info(f"Client connected: {sid}")
            await self.sio.emit('connection_established', {'status': 'connected'}, room=sid)

        @self.sio.event
        async def disconnect(sid):
            logger.info(f"Client disconnected: {sid}")

        # Можно добавить другие обработчики событий, которые инициируются клиентом

    async def emit_appointment_created(self, appointment_data: Dict[str, Any]):
        """Отправляет событие о создании новой записи"""
        logger.info(f"Emitting appointment_created event with data: {appointment_data}")
        await self.sio.emit('appointment_created', appointment_data)

    async def emit_appointment_updated(self, appointment_data: Dict[str, Any]):
        """Отправляет событие об обновлении записи"""
        logger.info(f"Emitting appointment_updated event with data: {appointment_data}")
        await self.sio.emit('appointment_updated', appointment_data)

    async def emit_customer_created(self, customer_data: Dict[str, Any]):
        """Отправляет событие о создании нового клиента"""
        logger.info(f"Emitting customer_created event with data: {customer_data}")
        await self.sio.emit('customer_created', customer_data)

    async def emit_document_uploaded(self, document_data: Dict[str, Any]):
        """Отправляет событие о загрузке документа"""
        logger.info(f"Emitting document_uploaded event with data: {document_data}")
        await self.sio.emit('document_uploaded', document_data)

# Создаем единственный экземпляр сервиса для использования в приложении
websocket_service = WebSocketService()