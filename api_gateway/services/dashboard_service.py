# api_gateway/services/dashboard_service.py
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta

from repositories.customer_repository import CustomerRepository
from repositories.appointment_repository import AppointmentRepository
from repositories.activity_repository import ActivityRepository


class DashboardService:
    def __init__(self, customer_repo: CustomerRepository, appointment_repo: AppointmentRepository,
                 activity_repo: ActivityRepository):
        self.customer_repo = customer_repo
        self.appointment_repo = appointment_repo
        self.activity_repo = activity_repo

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Получает статистику для дашборда"""
        with self.customer_repo.session_scope() as session:
            customer_repo = CustomerRepository(session)
            appointment_repo = AppointmentRepository(session)

            # Получаем общее количество клиентов
            total_customers = customer_repo.get_total_count()

            # Получаем количество новых клиентов за последний месяц
            month_ago = datetime.utcnow() - timedelta(days=30)
            new_customers = customer_repo.get_count_since(month_ago)

            # Получаем количество повторных клиентов
            repeat_customers = customer_repo.get_count_with_visits(min_visits=2)

            # Рассчитываем процент повторных клиентов
            returning_percentage = "0%"
            if total_customers > 0:
                returning_percentage = f"{round(repeat_customers / total_customers * 100)}%"

            # Получаем количество предстоящих записей
            today = date.today()
            upcoming_appointments = appointment_repo.get_count_since_date(today)

            # Рассчитываем тренды (для примера)
            # В реальном приложении нужно сравнивать с предыдущим периодом
            return {
                "total_customers": total_customers,
                "new_customers": new_customers,
                "returning_percentage": returning_percentage,
                "upcoming_appointments": upcoming_appointments,
                "total_customers_trend": {"direction": "up", "value": 12},
                "new_customers_trend": {"direction": "up", "value": 8},
                "returning_customers_trend": {"direction": "same", "value": 0},
                "scheduled_appointments_trend": {"direction": "down", "value": 5}
            }

    def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает последние активности для дашборда"""
        with self.activity_repo.session_scope() as session:
            activity_repo = ActivityRepository(session)

            activities = activity_repo.get_recent(limit)

            return [
                {
                    "id": str(activity.id),
                    "message": activity.message,
                    "type": activity.type,
                    "created_at": activity.created_at.isoformat(),
                    "customer": {
                        "id": str(activity.customer_id) if activity.customer_id else None,
                        "name": activity.customer.name if activity.customer else "Система"
                    }
                } for activity in activities
            ]

    def get_revenue_stats(self, period: str = "month") -> Dict[str, Any]:
        """Получает статистику по доходам за указанный период"""
        with self.appointment_repo.session_scope() as session:
            appointment_repo = AppointmentRepository(session)

            # Определяем начальную дату в зависимости от периода
            today = date.today()
            end_date = today
            if period == "week":
                start_date = today - timedelta(days=7)
                date_format = "%a"  # День недели
            elif period == "month":
                start_date = today.replace(day=1)
                date_format = "%d"  # День месяца
            elif period == "year":
                start_date = today.replace(month=1, day=1)
                date_format = "%b"  # Месяц
            else:
                # По умолчанию - месяц
                start_date = today.replace(day=1)
                date_format = "%d"

            # Получаем данные о доходах
            revenue_data = appointment_repo.get_revenue_in_range(start_date, end_date)

            # Форматируем данные для графика
            chart_data = []
            for item in revenue_data:
                chart_data.append({
                    "date": item["date"].strftime(date_format),
                    "revenue": float(item["revenue"]),
                    "count": item["count"]
                })

            # Рассчитываем общую сумму
            total_revenue = sum(float(item["revenue"]) for item in revenue_data)

            return {
                "period": period,
                "total_revenue": round(total_revenue, 2),
                "chart_data": chart_data
            }