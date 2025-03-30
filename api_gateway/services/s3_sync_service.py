# api_gateway/services/s3_sync_service.py
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import update
from datetime import datetime

from repositories.user_submission_repository import UserSubmissionRepository
from storage.s3_client import S3Service

logger = logging.getLogger(__name__)


class S3SyncService:
    """
    Сервис для синхронизации изменений в S3 с базой данных PostgreSQL
    """

    def __init__(self, s3_service: S3Service, user_submission_repo: UserSubmissionRepository):
        self.s3_service = s3_service
        self.user_submission_repo = user_submission_repo
        logger.info("S3SyncService initialized")

    def sync_file_changes(self, submission_id: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Синхронизирует изменения файла в S3 с базой данных PostgreSQL,
        сохраняя историю изменений вместо удаления старых версий

        Args:
            submission_id: ID заявки
            file_info: Информация о файле (имя, путь в S3, категория и т.д.)

        Returns:
            Dict с результатом операции
        """
        logger.info(f"Syncing file changes for submission_id: {submission_id}, file: {file_info.get('filename')}")

        try:
            with self.user_submission_repo.session_scope() as session:
                repo = UserSubmissionRepository(session)
                submission = repo.get_by_submission_id(submission_id)

                if not submission:
                    logger.warning(f"Submission {submission_id} not found in database")
                    return {
                        "status": "error",
                        "message": f"Submission {submission_id} not found"
                    }

                # Получаем текущие ссылки на файлы
                s3_file_links = submission.s3_file_links or {}
                category = file_info.get('category', 'files')

                # Создаем категорию, если она еще не существует
                if category not in s3_file_links:
                    s3_file_links[category] = []

                # Получаем информацию о файле
                filename = file_info.get('filename')
                s3_key = file_info.get('s3_key')

                if not filename or not s3_key:
                    logger.warning("Missing required file information")
                    return {
                        "status": "error",
                        "message": "Missing required file information"
                    }

                # Проверяем, существует ли файл уже в списке
                existing_file_index = None
                for idx, file_data in enumerate(s3_file_links[category]):
                    if isinstance(file_data, dict) and file_data.get('original_name') == filename:
                        existing_file_index = idx
                        break

                # Формируем URL для файла
                s3_url = f"https://{self.s3_service.bucket}.s3.amazonaws.com/{s3_key}"

                # Получаем текущее время для метки изменения
                now = datetime.utcnow().isoformat()

                # Подготавливаем обновленную информацию о файле
                updated_file_info = {
                    'original_name': filename,
                    's3_key': s3_key,
                    'url': s3_url,
                    'updated_at': now
                }

                # Если передан размер файла, добавляем его
                if 'size' in file_info:
                    updated_file_info['size'] = file_info['size']

                # Если передан тип содержимого, добавляем его
                if 'content_type' in file_info:
                    updated_file_info['content_type'] = file_info['content_type']

                # Если передана версия, добавляем её
                if 'version' in file_info:
                    updated_file_info['version'] = file_info['version']
                else:
                    # Если версия не передана, генерируем её на основе временной метки
                    updated_file_info['version'] = f"v{int(datetime.utcnow().timestamp())}"

                # Если файл с таким именем уже существует
                if existing_file_index is not None:
                    existing_file = s3_file_links[category][existing_file_index]

                    # Проверяем, есть ли уже история версий
                    if 'versions' not in existing_file:
                        existing_file['versions'] = []

                    # Сохраняем текущую версию в историю
                    existing_file_copy = existing_file.copy()

                    # Удаляем массив версий из копии, чтобы избежать дублирования
                    if 'versions' in existing_file_copy:
                        del existing_file_copy['versions']

                    # Добавляем копию текущей версии в историю
                    existing_file['versions'].append(existing_file_copy)

                    # Обновляем информацию о файле
                    existing_file.update(updated_file_info)
                    action = "updated"
                else:
                    # Иначе добавляем новый файл
                    updated_file_info['versions'] = []  # Инициализируем пустую историю версий
                    updated_file_info['created_at'] = now  # Добавляем время создания
                    s3_file_links[category].append(updated_file_info)

                    # Также обновляем список имен документов
                    document_names = submission.document_names or []
                    if filename not in document_names:
                        document_names.append(filename)
                        repo.update(submission.id, {'document_names': document_names})

                    action = "added"

                # Обновляем запись в базе данных
                repo.update(submission.id, {'s3_file_links': s3_file_links})

                logger.info(f"Successfully {action} file '{filename}' in submission {submission_id}")

                return {
                    "status": "success",
                    "message": f"File {action} successfully",
                    "filename": filename,
                    "s3_key": s3_key,
                    "url": s3_url,
                    "version": updated_file_info.get('version')
                }

        except Exception as e:
            logger.error(f"Error while syncing file changes: {str(e)}")
            return {
                "status": "error",
                "message": f"Error syncing file changes: {str(e)}"
            }

    def get_file_versions(self, submission_id: str, filename: str, category: str = "files") -> Dict[str, Any]:
        """
        Получает историю версий файла

        Args:
            submission_id: ID заявки
            filename: Имя файла
            category: Категория файла

        Returns:
            Dict с историей версий файла
        """
        logger.info(f"Getting file versions for submission_id: {submission_id}, file: {filename}")

        try:
            with self.user_submission_repo.session_scope() as session:
                repo = UserSubmissionRepository(session)
                submission = repo.get_by_submission_id(submission_id)

                if not submission:
                    logger.warning(f"Submission {submission_id} not found in database")
                    return {
                        "status": "error",
                        "message": f"Submission {submission_id} not found"
                    }

                # Получаем ссылки на файлы
                s3_file_links = submission.s3_file_links or {}

                if category not in s3_file_links:
                    logger.warning(f"Category {category} not found in submission {submission_id}")
                    return {
                        "status": "error",
                        "message": f"Category {category} not found"
                    }

                # Ищем файл в списке
                file_data = None
                for file_info in s3_file_links[category]:
                    if isinstance(file_info, dict) and file_info.get('original_name') == filename:
                        file_data = file_info
                        break

                if not file_data:
                    logger.warning(f"File {filename} not found in category {category}")
                    return {
                        "status": "error",
                        "message": f"File {filename} not found"
                    }

                # Получаем версии файла
                versions = file_data.get('versions', [])

                # Добавляем текущую версию в список
                current_version = file_data.copy()
                if 'versions' in current_version:
                    del current_version['versions']

                # Форматируем ответ
                result = {
                    "status": "success",
                    "filename": filename,
                    "current_version": current_version,
                    "versions": versions,
                    "version_count": len(versions)
                }

                return result

        except Exception as e:
            logger.error(f"Error while getting file versions: {str(e)}")
            return {
                "status": "error",
                "message": f"Error getting file versions: {str(e)}"
            }

    def delete_file_from_db(self, submission_id: str, filename: str, category: str = "files") -> Dict[str, Any]:
        """
        Удаляет информацию о файле из базы данных при удалении файла в S3

        Args:
            submission_id: ID заявки
            filename: Имя файла
            category: Категория файла

        Returns:
            Dict с результатом операции
        """
        logger.info(f"Deleting file info from DB for submission_id: {submission_id}, file: {filename}")

        try:
            with self.user_submission_repo.session_scope() as session:
                repo = UserSubmissionRepository(session)
                submission = repo.get_by_submission_id(submission_id)

                if not submission:
                    logger.warning(f"Submission {submission_id} not found in database")
                    return {
                        "status": "error",
                        "message": f"Submission {submission_id} not found"
                    }

                # Получаем текущие ссылки на файлы
                s3_file_links = submission.s3_file_links or {}

                if category not in s3_file_links:
                    logger.warning(f"Category {category} not found in submission {submission_id}")
                    return {
                        "status": "error",
                        "message": f"Category {category} not found"
                    }

                # Ищем файл в списке
                found = False
                updated_files = []

                for file_data in s3_file_links[category]:
                    if isinstance(file_data, dict) and file_data.get('original_name') == filename:
                        found = True
                    else:
                        updated_files.append(file_data)

                if not found:
                    logger.warning(f"File {filename} not found in category {category}")
                    return {
                        "status": "error",
                        "message": f"File {filename} not found"
                    }

                # Обновляем список файлов в категории
                s3_file_links[category] = updated_files

                # Также удаляем файл из списка имен документов, если он там был
                document_names = submission.document_names or []
                if filename in document_names:
                    document_names.remove(filename)
                    repo.update(submission.id, {'document_names': document_names})

                # Обновляем запись в базе данных
                repo.update(submission.id, {'s3_file_links': s3_file_links})

                logger.info(f"Successfully deleted file '{filename}' from submission {submission_id}")

                return {
                    "status": "success",
                    "message": "File deleted successfully",
                    "filename": filename
                }

        except Exception as e:
            logger.error(f"Error while deleting file info: {str(e)}")
            return {
                "status": "error",
                "message": f"Error deleting file info: {str(e)}"
            }

    def scan_and_sync_submission(self, submission_id: str) -> Dict[str, Any]:
        """
        Сканирует файлы в S3 для указанной заявки и синхронизирует их с базой данных

        Args:
            submission_id: ID заявки

        Returns:
            Dict с результатом операции
        """
        logger.info(f"Scanning and syncing files for submission_id: {submission_id}")

        try:
            # Формируем префикс для поиска файлов в S3
            prefix = f"{self.s3_service.base_path}{submission_id}/"

            # Получаем список объектов в S3
            s3_objects = self.s3_service.s3_client.list_objects_v2(
                Bucket=self.s3_service.bucket,
                Prefix=prefix
            )

            if 'Contents' not in s3_objects:
                logger.warning(f"No files found in S3 for submission {submission_id}")
                return {
                    "status": "warning",
                    "message": "No files found in S3"
                }

            # Получаем данные о заявке из базы данных
            with self.user_submission_repo.session_scope() as session:
                repo = UserSubmissionRepository(session)
                submission = repo.get_by_submission_id(submission_id)

                if not submission:
                    logger.warning(f"Submission {submission_id} not found in database")
                    return {
                        "status": "error",
                        "message": f"Submission {submission_id} not found"
                    }

                # Получаем текущие ссылки на файлы
                s3_file_links = submission.s3_file_links or {}
                document_names = submission.document_names or []

                # Подготавливаем структуру для обновленных данных
                updated_s3_file_links = {}
                updated_document_names = set(document_names)

                # Обрабатываем каждый объект в S3
                for obj in s3_objects['Contents']:
                    s3_key = obj['Key']

                    # Пропускаем директории
                    if s3_key.endswith('/'):
                        continue

                    # Определяем категорию и имя файла
                    path_parts = s3_key.replace(prefix, '').split('/')

                    if len(path_parts) > 1:
                        category = path_parts[0]
                        filename = '/'.join(path_parts[1:])
                    else:
                        category = 'files'
                        filename = path_parts[0]

                    # Добавляем категорию, если её еще нет
                    if category not in updated_s3_file_links:
                        updated_s3_file_links[category] = []

                    # Формируем URL для файла
                    s3_url = f"https://{self.s3_service.bucket}.s3.amazonaws.com/{s3_key}"

                    # Добавляем информацию о файле
                    file_info = {
                        'original_name': filename,
                        's3_key': s3_key,
                        'url': s3_url,
                        'last_modified': obj['LastModified'].isoformat()
                    }

                    updated_s3_file_links[category].append(file_info)
                    updated_document_names.add(filename)

                # Обновляем запись в базе данных
                repo.update(submission.id, {
                    's3_file_links': updated_s3_file_links,
                    'document_names': list(updated_document_names)
                })

                logger.info(f"Successfully synchronized all files for submission {submission_id}")

                return {
                    "status": "success",
                    "message": "Files synchronized successfully",
                    "file_count": len(s3_objects['Contents']) - 1,
                    # Вычитаем 1, т.к. корневая директория тоже считается объектом
                    "categories": list(updated_s3_file_links.keys())
                }

        except Exception as e:
            logger.error(f"Error while scanning and syncing files: {str(e)}")
            return {
                "status": "error",
                "message": f"Error scanning and syncing files: {str(e)}"
            }