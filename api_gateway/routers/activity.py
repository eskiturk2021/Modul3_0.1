# api_gateway/routers/activity.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.activity_service import ActivityService
from dependencies import get_activity_service

router = APIRouter()

@router.get("/activity/recent", response_model=List[Dict[str, Any]])
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    activity_service: ActivityService = Depends(get_activity_service)
):
    """
    Получение последних активностей
    """
    try:
        activities = activity_service.get_recent_activity(limit=limit, offset=offset)
        return activities
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении активности: {str(e)}")

@router.get("/activity/customer/{customer_id}", response_model=List[Dict[str, Any]])
async def get_customer_activity(
    customer_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    activity_service: ActivityService = Depends(get_activity_service)
):
    """
    Получение активностей конкретного клиента
    """
    try:
        activities = activity_service.get_customer_activity(customer_id, limit, offset)
        return activities
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении активности клиента: {str(e)}")

@router.post("/activity/log", response_model=Dict[str, Any])
async def log_activity(
    activity_data: Dict[str, Any],
    activity_service: ActivityService = Depends(get_activity_service)
):
    """
    Логирование новой активности
    """
    try:
        result = activity_service.log_activity(activity_data)
        return {
            "status": "success",
            "id": result.get("id"),
            "message": "Активность успешно записана"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при логировании активности: {str(e)}")

# Мок-данные для тестирования в случае недоступности микросервиса
@router.get("/activity/recent/mock", response_model=List[Dict[str, Any]])
async def get_mock_activity():
    """
    Возвращает моковые данные активности для тестирования
    """
    return [
        {
            "id": "act-1",
            "message": "New appointment created",
            "type": "appointment",
            "created_at": datetime.now().isoformat(),
            "customer": {
                "id": "cust-1",
                "name": "John Doe"
            }
        },
        {
            "id": "act-2",
            "message": "Customer profile updated",
            "type": "customer",
            "created_at": datetime.now().isoformat(),
            "customer": {
                "id": "cust-2",
                "name": "Jane Smith"
            }
        },
        {
            "id": "act-3",
            "message": "Document uploaded",
            "type": "document",
            "created_at": datetime.now().isoformat(),
            "customer": {
                "id": "cust-1",
                "name": "John Doe"
            }
        }
    ]