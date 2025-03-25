# api_gateway/routers/customers.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from services.customer_service import CustomerService
from dependencies import get_customer_service
from fastapi import Response
import csv
from io import StringIO
from datetime import datetime

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


@router.get("/customers/export", response_class=Response)
async def export_customers(
        search: Optional[str] = None,
        customer_service: CustomerService = Depends(get_customer_service)
):
    """
    Экспорт списка клиентов в формате CSV
    """
    try:
        # Получаем данные клиентов (здесь используем большое значение limit)
        result = customer_service.get_customers(search, limit=10000, offset=0)
        customers = result.get("customers", [])

        # Создаем CSV в памяти
        output = StringIO()
        writer = csv.writer(output)

        # Пишем заголовки
        writer.writerow([
            "ID", "Имя", "Телефон", "Марка автомобиля",
            "Модель автомобиля", "Год выпуска", "Последний визит"
        ])

        # Пишем данные
        for customer in customers:
            writer.writerow([
                customer.get("id", ""),
                customer.get("name", ""),
                customer.get("phone", ""),
                customer.get("vehicle_make", ""),
                customer.get("vehicle_model", ""),
                customer.get("vehicle_year", ""),
                customer.get("last_visit", "")
            ])

        # Подготавливаем ответ
        response = Response(
            content=output.getvalue(),
            media_type="text/csv"
        )

        # Добавляем заголовок для скачивания файла
        filename = f"customers_export_{datetime.utcnow().strftime('%Y-%m-%d')}.csv"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при экспорте клиентов: {str(e)}")