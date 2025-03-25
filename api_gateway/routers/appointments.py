# api_gateway/routers/appointments.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import date, datetime, time

from services.appointment_service import AppointmentService
from dependencies import get_appointment_service

router = APIRouter()

class AppointmentBase(BaseModel):
    customer_id: str
    service_type: str
    appointment_date: date
    appointment_time: time
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    service_type: Optional[str] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    status: Optional[str] = None
    notes: Optional[str] = None

@router.get("/appointments/upcoming", response_model=List[Dict[str, Any]])
async def get_upcoming_appointments(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """
    Получение предстоящих записей на обслуживание
    """
    try:
        appointments = appointment_service.get_upcoming_appointments(limit, offset)
        return appointments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записей: {str(e)}")

@router.get("/appointments/{appointment_id}", response_model=Dict[str, Any])
async def get_appointment(
    appointment_id: str = Path(..., title="ID записи"),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """
    Получение информации о конкретной записи
    """
    try:
        appointment = appointment_service.get_appointment_by_id(appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        return appointment
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записи: {str(e)}")

@router.post("/appointments", response_model=Dict[str, Any])
async def create_appointment(
    appointment: AppointmentCreate = Body(...),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """
    Создание новой записи на обслуживание
    """
    try:
        result = appointment_service.create_appointment(appointment.dict())
        return {
            "id": result.get("id"),
            "status": "success",
            "message": "Запись успешно создана"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при создании записи: {str(e)}")

@router.put("/appointments/{appointment_id}", response_model=Dict[str, Any])
async def update_appointment(
    appointment_id: str = Path(..., title="ID записи"),
    appointment_data: AppointmentUpdate = Body(...),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """
    Обновление информации о записи
    """
    try:
        updated = appointment_service.update_appointment(appointment_id, appointment_data.dict(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        return {
            "status": "success",
            "message": "Запись успешно обновлена"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении записи: {str(e)}")

@router.delete("/appointments/{appointment_id}", response_model=Dict[str, Any])
async def cancel_appointment(
    appointment_id: str = Path(..., title="ID записи"),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """
    Отмена записи
    """
    try:
        cancelled = appointment_service.cancel_appointment(appointment_id)
        if not cancelled:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        return {
            "status": "success",
            "message": "Запись успешно отменена"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при отмене записи: {str(e)}")

@router.get("/appointments/calendar", response_model=List[Dict[str, Any]])
async def get_calendar_appointments(
    year: int = Query(..., title="Год"),
    month: int = Query(..., ge=1, le=12, title="Месяц (1-12)"),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """
    Получение записей для календаря на указанный месяц
    """
    try:
        calendar_data = appointment_service.get_calendar_appointments(year, month)
        return calendar_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении календаря: {str(e)}")

@router.get("/appointments/slots", response_model=List[Dict[str, Any]])
async def get_available_slots(
    date: date = Query(..., title="Дата"),
    appointment_service: AppointmentService = Depends(get_appointment_service)
):
    """
    Получение доступных слотов для записи на указанную дату
    """
    try:
        slots = appointment_service.get_available_slots(date)
        return slots
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении доступных слотов: {str(e)}")