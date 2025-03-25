# api_gateway/routers/dashboard.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from api_gateway.services.dashboard_service import DashboardService
from api_gateway.dependencies import get_dashboard_service

router = APIRouter()


@router.get("/dashboard/stats", response_model=Dict[str, Any])
async def get_dashboard_stats(
        dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Получение статистики для дашборда
    """
    try:
        stats = dashboard_service.get_dashboard_stats()

        # Приводим ответ к формату, ожидаемому фронтендом
        return {
            "totalCustomers": stats.get("total_customers", 0),
            "totalCustomersTrend": stats.get("total_customers_trend", {
                "direction": "up",
                "value": 12
            }),
            "newCustomers": stats.get("new_customers", 0),
            "newCustomersTrend": stats.get("new_customers_trend", {
                "direction": "up",
                "value": 8
            }),
            "returningCustomersPercentage": stats.get("returning_percentage", "0%"),
            "returningCustomersTrend": stats.get("returning_customers_trend", {
                "direction": "same",
                "value": 0
            }),
            "scheduledAppointments": stats.get("upcoming_appointments", 0),
            "scheduledAppointmentsTrend": stats.get("scheduled_appointments_trend", {
                "direction": "down",
                "value": 5
            })
        }
    except Exception as e:
        # Добавляем подробное логирование ошибки
        print(f"Error in get_dashboard_stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики: {str(e)}")


@router.get("/dashboard/recent-activity", response_model=Dict[str, Any])
async def get_recent_activity(
        limit: int = 10,
        dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Получение последних активностей для дашборда
    """
    try:
        activity = dashboard_service.get_recent_activity(limit)
        return {
            "activities": activity,
            "total": len(activity)
        }
    except Exception as e:
        print(f"Error in get_recent_activity: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении активностей: {str(e)}")


@router.get("/dashboard/revenue", response_model=Dict[str, Any])
async def get_revenue_stats(
        period: str = "month",
        dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Получение статистики по доходам за указанный период
    """
    try:
        revenue_data = dashboard_service.get_revenue_stats(period)
        return revenue_data
    except Exception as e:
        print(f"Error in get_revenue_stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики доходов: {str(e)}")