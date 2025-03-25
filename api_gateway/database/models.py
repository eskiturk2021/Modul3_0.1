# api_gateway/database/models.py
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from datetime import datetime
from .postgresql import Base


# Модели должны точно отражать существующую структуру таблиц,
# созданных модулем 2

class UserSubmission(Base):
    __tablename__ = 'user_submissions'

    id = sa.Column(sa.Integer, primary_key=True)
    submission_id = sa.Column(sa.String, unique=True, nullable=False)
    company_name = sa.Column(sa.String)
    email = sa.Column(sa.String)
    phone = sa.Column(sa.String)
    city = sa.Column(sa.String)
    business_type = sa.Column(sa.String)
    document_names = sa.Column(ARRAY(sa.String))
    s3_file_links = sa.Column(JSONB)
    submission_data = sa.Column(JSONB)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


class Customer(Base):
    __tablename__ = 'customers'

    id = sa.Column(sa.Integer, primary_key=True)
    customer_id = sa.Column(sa.String(20), unique=True)
    phone = sa.Column(sa.String(30), unique=True, nullable=False)
    name = sa.Column(sa.String(100))
    vehicle_make = sa.Column(sa.String)
    vehicle_model = sa.Column(sa.String)
    vehicle_year = sa.Column(sa.String)
    last_visit = sa.Column(sa.DateTime)
    total_visits = sa.Column(sa.Integer, default=0)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = 'messages'

    id = sa.Column(sa.Integer, primary_key=True)
    phone_id = sa.Column(sa.String(30))
    phone = sa.Column(sa.String(30), nullable=False)
    message_type = sa.Column(sa.String(20), nullable=False)
    message_text = sa.Column(sa.Text, nullable=False)
    thread_id = sa.Column(sa.String(50))
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


class Appointment(Base):
    __tablename__ = 'appointments'

    id = sa.Column(sa.Integer, primary_key=True)
    appointment_id = sa.Column(sa.String(30), unique=True, nullable=False)
    customer_phone = sa.Column(sa.String(30), nullable=False)
    customer_name = sa.Column(sa.String(100), nullable=False)
    vehicle_make = sa.Column(sa.String)
    vehicle_model = sa.Column(sa.String)
    vehicle_year = sa.Column(sa.String)
    service_type = sa.Column(sa.String(50), nullable=False)
    appointment_date = sa.Column(sa.Date, nullable=False)
    appointment_time = sa.Column(sa.Time, nullable=False)
    estimated_cost = sa.Column(sa.Numeric(10, 2))
    status = sa.Column(sa.String(20), default='pending')
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


class AvailableSlot(Base):
    __tablename__ = 'available_slots'

    id = sa.Column(sa.Integer, primary_key=True)
    date = sa.Column(sa.Date, nullable=False)
    time = sa.Column(sa.Time, nullable=False)
    is_available = sa.Column(sa.Boolean, default=True)
    __table_args__ = (sa.UniqueConstraint('date', 'time', name='unique_date_time'),)

# api_gateway/database/models.py (дополнение для User)

class User(Base):
    """
    Модель пользователя системы
    """
    __tablename__ = "users"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    username = sa.Column(sa.String(50), unique=True, index=True, nullable=False)
    email = sa.Column(sa.String(100), unique=True, index=True)
    password = sa.Column(sa.String(255), nullable=False)  # Хранится хешированный пароль
    role = sa.Column(sa.String(20), default="user")  # user, admin
    refresh_token = sa.Column(sa.String(255), nullable=True)
    last_login = sa.Column(sa.DateTime, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)