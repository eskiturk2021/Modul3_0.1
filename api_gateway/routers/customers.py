# api_gateway/routers/customers.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from ..services.customer_service import CustomerService
from ..dependencies import get_customer_service

router = APIRouter()

class CustomerBase(BaseModel):
    name: str
    phone: str
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[str] = None

@router.get("/customers", response_model=Dict[str, Any])
async def get_customers(
    search: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """
    Получение списка клиентов с возможностью поиска
    """
    try:
        result = customer_service.get_customers(search, limit, offset)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении клиентов: {str(e)}")

@router.get("/customers/{customer_id}", response_model=Dict[str, Any])
async def get_customer(
    customer_id: str = Path(..., title="ID клиента"),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """
    Получение информации о конкретном клиенте
    """
    try:
        customer = customer_service.get_customer_by_id(customer_id)
        return customer
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных клиента: {str(e)}")

@router.post("/customers", response_model=Dict[str, Any])
async def create_customer(
    customer: CustomerCreate = Body(...),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """
    Создание нового клиента
    """
    try:
        result = customer_service.create_customer(customer.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при создании клиента: {str(e)}")