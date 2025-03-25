from fastapi import Depends, Request, HTTPException
from typing import Generator
from sqlalchemy.orm import Session

from database.postgresql import DatabaseService
from storage.s3_client import S3Service

# Добавить импорты для репозиториев
from repositories.user_submission_repository import UserSubmissionRepository
from repositories.customer_repository import CustomerRepository
from repositories.appointment_repository import AppointmentRepository
from repositories.message_repository import MessageRepository
from repositories.activity_repository import ActivityRepository  # Добавить этот импорт
from repositories.available_slot_repository import AvailableSlotRepository  # Добавить этот импорт
from repositories.service_repository import ServiceRepository  # Добавить этот импорт
from repositories.user_repository import UserRepository  # Добавить этот импорт

# Добавить импорты для сервисов
from services.document_service import DocumentService
from services.customer_service import CustomerService
from services.dashboard_service import DashboardService  # Добавить этот импорт
from services.activity_service import ActivityService  # Добавить этот импорт
from services.appointment_service import AppointmentService  # Добавить этот импорт
from services.settings_service import SettingsService  # Добавить этот импорт
from services.auth_service import AuthService  # Добавить этот импорт

from config import settings

# Создаем экземпляры сервисов
db_service = DatabaseService(settings.DATABASE_URL)
s3_service = S3Service(
    aws_access_key=settings.S3_AWS_ACCESS_KEY,
    aws_secret_key=settings.S3_AWS_SECRET_KEY,
    region=settings.S3_REGION,
    bucket=settings.S3_BUCKET,
    base_path=settings.S3_BASE_PATH
)

def get_db_session() -> Generator[Session, None, None]:
    with db_service.session_scope() as session:
        yield session

# Репозитории следующими
def get_user_submission_repo(session: Session = Depends(get_db_session)) -> UserSubmissionRepository:
    return UserSubmissionRepository(session)

def get_customer_repo(session: Session = Depends(get_db_session)) -> CustomerRepository:
    return CustomerRepository(session)

def get_appointment_repo(session: Session = Depends(get_db_session)) -> AppointmentRepository:
    return AppointmentRepository(session)

def get_message_repo(session: Session = Depends(get_db_session)) -> MessageRepository:
    return MessageRepository(session)

def get_activity_repo(session: Session = Depends(get_db_session)) -> ActivityRepository:
    return ActivityRepository(session)

def get_available_slot_repo(session: Session = Depends(get_db_session)) -> AvailableSlotRepository:
    return AvailableSlotRepository(session)

def get_service_repo(session: Session = Depends(get_db_session)) -> ServiceRepository:
    return ServiceRepository(session)

def get_user_repo(session: Session = Depends(get_db_session)) -> UserRepository:
    return UserRepository(session)

# Сервисы последними, так как они зависят от репозиториев
def get_document_service(
    user_submission_repo: UserSubmissionRepository = Depends(get_user_submission_repo)
) -> DocumentService:
    return DocumentService(s3_service, user_submission_repo)

def get_customer_service(
    customer_repo: CustomerRepository = Depends(get_customer_repo),
    appointment_repo: AppointmentRepository = Depends(get_appointment_repo),
    message_repo: MessageRepository = Depends(get_message_repo)
) -> CustomerService:
    return CustomerService(customer_repo, appointment_repo, message_repo)

def get_dashboard_service(
    customer_repo: CustomerRepository = Depends(get_customer_repo),
    appointment_repo: AppointmentRepository = Depends(get_appointment_repo),
    activity_repo: ActivityRepository = Depends(get_activity_repo)
) -> DashboardService:
    return DashboardService(customer_repo, appointment_repo, activity_repo)

def get_activity_service(
    activity_repo: ActivityRepository = Depends(get_activity_repo),
    customer_repo: CustomerRepository = Depends(get_customer_repo)
) -> ActivityService:
    return ActivityService(activity_repo, customer_repo)

def get_appointment_service(
    appointment_repo: AppointmentRepository = Depends(get_appointment_repo),
    customer_repo: CustomerRepository = Depends(get_customer_repo),
    slot_repo: AvailableSlotRepository = Depends(get_available_slot_repo)
) -> AppointmentService:
    return AppointmentService(appointment_repo, customer_repo, slot_repo)

def get_settings_service(
    service_repo: ServiceRepository = Depends(get_service_repo)
) -> SettingsService:
    return SettingsService(service_repo, s3_service)

def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo)
) -> AuthService:
    return AuthService(user_repo)


