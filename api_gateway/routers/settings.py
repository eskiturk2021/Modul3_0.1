# api_gateway/routers/settings.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from services.settings_service import SettingsService
from dependencies import get_settings_service
from datetime import datetime

router = APIRouter()

class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration: int
    price: float
    category: Optional[str] = "maintenance"

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    price: Optional[float] = None
    category: Optional[str] = None
    active: Optional[bool] = None

# Эндпоинт для получения системных настроек
@router.get("/settings/system", response_model=Dict[str, Any])
async def get_system_settings(
    settings_service: SettingsService = Depends(get_settings_service)
):
    """
    Получение системных настроек
    """
    try:
        settings = settings_service.get_system_settings()
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении настроек: {str(e)}")

# Эндпоинт для обновления системного промпта
# Дополнение к файлу routers/settings.py
@router.put("/system/prompt", response_model=Dict[str, Any])
async def update_system_prompt_alternative(
        content: Dict[str, str] = Body(...),
        settings_service: SettingsService = Depends(get_settings_service)
):
    """
    Альтернативный эндпоинт для обновления системного промпта
    """
    try:
        prompt_content = content.get("content", "")
        if not prompt_content:
            raise HTTPException(status_code=400, detail="Content is required")

        success = settings_service.update_system_prompt(prompt_content)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update system prompt")
        return {
            "status": "success",
            "message": "System prompt updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating system prompt: {str(e)}")
# Эндпоинт для получения сервисов
@router.get("/settings/services", response_model=Dict[str, Any])
async def get_services(
    settings_service: SettingsService = Depends(get_settings_service)
):
    """
    Получение списка доступных услуг
    """
    try:
        services = settings_service.get_services()
        return {
            "services": services
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении услуг: {str(e)}")

# Эндпоинт для добавления сервиса
@router.post("/settings/services", response_model=Dict[str, Any])
async def create_service(
    service: ServiceCreate = Body(...),
    settings_service: SettingsService = Depends(get_settings_service)
):
    """
    Добавление новой услуги
    """
    try:
        result = settings_service.create_service(service.dict())
        return {
            "id": result.get("id"),
            "status": "success",
            "message": "Услуга успешно добавлена"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при добавлении услуги: {str(e)}")

# Эндпоинт для обновления сервиса
@router.put("/settings/services/{service_id}", response_model=Dict[str, Any])
async def update_service(
    service_id: str = Path(..., title="ID услуги"),
    service_data: ServiceUpdate = Body(...),
    settings_service: SettingsService = Depends(get_settings_service)
):
    """
    Обновление услуги
    """
    try:
        success = settings_service.update_service(service_id, service_data.dict(exclude_unset=True))
        if not success:
            raise HTTPException(status_code=404, detail="Услуга не найдена")
        return {
            "status": "success",
            "message": "Услуга успешно обновлена"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении услуги: {str(e)}")

# Эндпоинт для удаления сервиса
@router.delete("/settings/services/{service_id}", response_model=Dict[str, Any])
async def delete_service(
    service_id: str = Path(..., title="ID услуги"),
    settings_service: SettingsService = Depends(get_settings_service)
):
    """
    Удаление услуги
    """
    try:
        success = settings_service.delete_service(service_id)
        if not success:
            raise HTTPException(status_code=404, detail="Услуга не найдена")
        return {
            "status": "success",
            "message": "Услуга успешно удалена"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении услуги: {str(e)}")

# Эндпоинт для получения рабочих часов
@router.get("/settings/working-hours", response_model=Dict[str, Any])
async def get_working_hours(
    settings_service: SettingsService = Depends(get_settings_service)
):
    """
    Получение рабочих часов
    """
    try:
        working_hours = settings_service.get_working_hours()
        return working_hours
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении рабочих часов: {str(e)}")

# Эндпоинт для обновления рабочих часов
@router.put("/settings/working-hours", response_model=Dict[str, Any])
async def update_working_hours(
    working_hours: Dict[str, Any] = Body(...),
    settings_service: SettingsService = Depends(get_settings_service)
):
    """
    Обновление рабочих часов
    """
    try:
        success = settings_service.update_working_hours(working_hours)
        if not success:
            raise HTTPException(status_code=500, detail="Не удалось обновить рабочие часы")
        return {
            "status": "success",
            "message": "Рабочие часы успешно обновлены"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении рабочих часов: {str(e)}")

# Добавьте следующий код в файл routers/settings.py или создайте новый файл routers/system.py

@router.get("/system/prompt", response_model=Dict[str, Any])
async def get_system_prompt(
    settings_service: SettingsService = Depends(get_settings_service)
):
    """
    Получение системного промпта
    """
    try:
        system_settings = settings_service.get_system_settings()
        return {
            "prompt": system_settings.get("system_prompt", ""),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении системного промпта: {str(e)}")