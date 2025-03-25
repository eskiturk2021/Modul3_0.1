# api_gateway/services/document_service.py
import uuid
from typing import Dict, List, Any, Optional, BinaryIO
from fastapi import UploadFile
import os
from datetime import datetime

from storage.s3_client import S3Service
from repositories.user_submission_repository import UserSubmissionRepository
from services.websocket_service import websocket_service
import asyncio

class DocumentService:
    def __init__(self, s3_service: S3Service, user_submission_repo: UserSubmissionRepository):
        self.s3_service = s3_service
        self.user_submission_repo = user_submission_repo

    async def upload_document(self, submission_id: str, file: UploadFile, category: str = "files") -> Dict:
        """Загружает документ в S3 и обновляет метаданные в БД"""
        file_content = await file.read()

        # Генерируем имя файла
        filename = f"{uuid.uuid4().hex}_{file.filename}"

        # Формируем путь к файлу
        file_path = f"{self.s3_service.base_path}{submission_id}/{category}/{filename}"

        # Загружаем файл в S3
        file_data = self.s3_service.upload_file(
            file_content,
            file_path,
            file.content_type
        )

        # Получаем запись о запросе
        with self.user_submission_repo.session_scope() as session:
            repo = UserSubmissionRepository(session)
            submission = repo.get_by_submission_id(submission_id)

            if submission:
                # Обновляем список файлов
                document_names = submission.document_names or []
                document_names.append(file.filename)

                # Обновляем ссылки на файлы
                s3_file_links = submission.s3_file_links or {}
                if category not in s3_file_links:
                    s3_file_links[category] = []

                s3_file_links[category].append({
                    'original_name': file.filename,
                    's3_key': file_path,
                    'url': file_data['url'],
                    'uploaded_at': datetime.utcnow().isoformat()
                })

                # Сохраняем изменения
                repo.update(submission.id, {
                    'document_names': document_names,
                    's3_file_links': s3_file_links
                })

        document_data = {
            'filename': file.filename,
            's3_key': file_path,
            'submission_id': submission_id,
            'category': category,
            'content_type': file.content_type,
            'size': len(file_content)
        }

        # Запускаем задачу отправки события
        asyncio.create_task(websocket_service.emit_document_uploaded(document_data))

        return {
            'filename': file.filename,
            's3_key': file_path,
            'submission_id': submission_id,
            'category': category
        }

    def get_document(self, submission_id: str, filename: str, category: str = "files") -> Dict:
        """Получает документ из S3 по идентификатору запроса и имени файла"""
        with self.user_submission_repo.session_scope() as session:
            repo = UserSubmissionRepository(session)
            submission = repo.get_by_submission_id(submission_id)

            if not submission or not submission.s3_file_links:
                raise ValueError(f"Submission {submission_id} not found or has no files")

            # Ищем файл в ссылках
            s3_file_links = submission.s3_file_links
            if category not in s3_file_links:
                raise ValueError(f"Category {category} not found in submission {submission_id}")

            file_info = None
            for file in s3_file_links[category]:
                if file['original_name'] == filename:
                    file_info = file
                    break

            if not file_info:
                raise ValueError(f"File {filename} not found in submission {submission_id}")

            # Получаем файл из S3
            file_data = self.s3_service.get_file(file_info['s3_key'])

            # Генерируем временную ссылку для скачивания
            download_url = self.s3_service.get_presigned_url(file_info['s3_key'])

            return {
                'filename': filename,
                's3_key': file_info['s3_key'],
                'content_type': file_data['content_type'],
                'content_length': file_data['content_length'],
                'download_url': download_url,
                'last_modified': file_data['last_modified']
            }

    def get_all_documents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получает список всех документов"""
        # Так как документы хранятся в S3 и информация о них внутри user_submissions,
        # нам нужно извлечь эти данные из базы данных
        documents = []

        with self.user_submission_repo.session_scope() as session:
            repo = UserSubmissionRepository(session)
            submissions = repo.get_all(limit=limit, offset=offset)

            # Обрабатываем каждую запись и извлекаем информацию о документах
            for submission in submissions:
                if not submission.s3_file_links:
                    continue

                for category, files in submission.s3_file_links.items():
                    for file_info in files:
                        doc = {
                            'submission_id': submission.submission_id,
                            'original_name': file_info.get('original_name', ''),
                            's3_key': file_info.get('s3_key', ''),
                            'url': file_info.get('url', ''),
                            'uploaded_at': file_info.get('uploaded_at', ''),
                            'category': category,
                            'company_name': submission.company_name,
                            'email': submission.email,
                            'phone': submission.phone
                        }

                        # Генерируем временный URL для доступа
                        try:
                            download_url = self.s3_service.get_presigned_url(file_info.get('s3_key', ''))
                            doc['download_url'] = download_url
                        except Exception:
                            doc['download_url'] = None

                        documents.append(doc)

        return documents