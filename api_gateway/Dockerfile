# api_gateway/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Переменные среды по умолчанию (подходят для локальной разработки)
ENV DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
ENV S3_AWS_ACCESS_KEY=your-access-key
ENV S3_AWS_SECRET_KEY=your-secret-key
ENV S3_REGION=us-east-1
ENV S3_BUCKET=your-bucket-name
ENV S3_BASE_PATH=user_data/
ENV API_KEY=change-me-in-production

# Порт, который будет слушать приложение
EXPOSE 8000

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]