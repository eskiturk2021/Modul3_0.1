# api_gateway/services/settings_service.py
from typing import Dict, List, Any, Optional
import json
import uuid

# Используем абсолютные импорты
from repositories.service_repository import ServiceRepository
from storage.s3_client import S3Service


class SettingsService:
    def __init__(self, service_repo: ServiceRepository, s3_service: S3Service):
        self.service_repo = service_repo
        self.s3_service = s3_service
        # Оригинальный путь к настройкам (сохраняем для обратной совместимости)
        self.system_settings_key = "system_settings/config.json"
        # Новый путь к файлу системного промпта в S3
        self.system_prompt_key = "user_data/9ba1beaf-09e6-4c72-b4cb-dae476404178/assistant_responses/system_prompt.txt"

    def get_system_settings(self) -> Dict[str, Any]:
        """Получает системные настройки"""
        try:
            with self.service_repo.session_scope() as session:
                # Сначала попытка загрузить системный промпт из текстового файла
                try:
                    file_data = self.s3_service.get_file(self.system_prompt_key)
                    system_prompt = file_data['body'].read().decode('utf-8')

                    # Создаем структуру настроек с полученным промптом
                    settings = {
                        "system_prompt": system_prompt,
                        "working_hours": {
                            "start": 8,
                            "end": 18,
                            "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                        },
                        "appointment_duration": 30,
                        "notification_enabled": True
                    }
                    return settings
                except Exception as e:
                    # Если текстовый файл не найден, пытаемся загрузить из JSON
                    try:
                        file_data = self.s3_service.get_file(self.system_settings_key)
                        settings_json = file_data['body'].read().decode('utf-8')
                        settings = json.loads(settings_json)
                        return settings
                    except Exception as json_e:
                        # Если JSON не найден или произошла ошибка, возвращаем настройки по умолчанию
                        settings = {
                            "system_prompt": "You are a helpful assistant that provides information about automotive services.",
                            "working_hours": {
                                "start": 8,
                                "end": 18,
                                "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                            },
                            "appointment_duration": 30,  # в минутах
                            "notification_enabled": True
                        }
                        return settings
        except Exception as e:
            # В случае ошибки возвращаем базовые настройки
            return {
                "system_prompt": "You are a helpful assistant that provides information about automotive services.",
                "working_hours": {
                    "start": 8,
                    "end": 18,
                    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                },
                "appointment_duration": 30,
                "notification_enabled": True
            }

    def update_system_prompt(self, content: str) -> bool:
        """Обновляет системный промпт"""
        try:
            # Сохраняем промпт в текстовом формате по новому пути
            success_txt = False
            try:
                self.s3_service.upload_file(
                    content.encode('utf-8'),
                    self.system_prompt_key,
                    "text/plain"
                )
                success_txt = True
            except Exception as txt_e:
                print(f"Error updating system prompt as TXT: {str(txt_e)}")

            # Также обновляем JSON-версию для обратной совместимости
            success_json = False
            try:
                # Получаем текущие настройки
                settings = self.get_system_settings()

                # Обновляем системный промпт
                settings["system_prompt"] = content

                # Сохраняем обновленные настройки
                settings_json = json.dumps(settings, indent=2)
                self.s3_service.upload_file(
                    settings_json.encode('utf-8'),
                    self.system_settings_key,
                    "application/json"
                )
                success_json = True
            except Exception as json_e:
                print(f"Error updating system prompt as JSON: {str(json_e)}")

            # Возвращаем успех, если хотя бы один формат был обновлен
            return success_txt or success_json
        except Exception as e:
            print(f"Error in update_system_prompt: {str(e)}")
            return False

    def get_services(self) -> List[Dict[str, Any]]:
        """Получает список услуг"""
        with self.service_repo.session_scope() as session:
            repo = ServiceRepository(session)

            # Получаем активные услуги
            services = repo.get_active_services()

            return [
                {
                    "id": service.service_id,
                    "name": service.name,
                    "description": service.description,
                    "duration": service.duration,
                    "price": float(service.price),
                    "category": service.category
                } for service in services
            ]

    def create_service(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новую услугу"""
        with self.service_repo.session_scope() as session:
            repo = ServiceRepository(session)

            # Создаем уникальный ID для услуги
            service_id = f"SRV-{uuid.uuid4().hex[:8].upper()}"

            # Дополняем данные услуги
            service_data["service_id"] = service_id
            service_data["active"] = True

            # Создаем услугу
            service = repo.create(service_data)

            return {
                "id": service.service_id,
                "name": service.name
            }

    def update_service(self, service_id: str, service_data: Dict[str, Any]) -> bool:
        """Обновляет информацию об услуге"""
        with self.service_repo.session_scope() as session:
            repo = ServiceRepository(session)

            # Получаем услугу по ID
            service = repo.get_by_service_id(service_id)
            if not service:
                return False

            # Обновляем услугу
            repo.update(service.id, service_data)

            return True

    def delete_service(self, service_id: str) -> bool:
        """Удаляет услугу (делает неактивной)"""
        with self.service_repo.session_scope() as session:
            repo = ServiceRepository(session)

            # Получаем услугу по ID
            service = repo.get_by_service_id(service_id)
            if not service:
                return False

            # Помечаем услугу как неактивную
            repo.update(service.id, {"active": False})

            return True

    def get_working_hours(self) -> Dict[str, Any]:
        """Получает рабочие часы"""
        settings = self.get_system_settings()
        return settings.get("working_hours", {
            "start": 8,
            "end": 18,
            "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        })

    def update_working_hours(self, working_hours: Dict[str, Any]) -> bool:
        """Обновляет рабочие часы"""
        try:
            # Получаем текущие настройки
            settings = self.get_system_settings()

            # Обновляем рабочие часы
            settings["working_hours"] = working_hours

            # Сохраняем обновленные настройки
            settings_json = json.dumps(settings, indent=2)
            self.s3_service.upload_file(
                settings_json.encode('utf-8'),
                self.system_settings_key,
                "application/json"
            )

            return True
        except Exception as e:
            print(f"Error updating working hours: {str(e)}")
            return False