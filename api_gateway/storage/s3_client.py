# api_gateway/storage/s3_client.py
import boto3
import os
import traceback
from botocore.exceptions import ClientError, BotoCoreError, NoCredentialsError
from typing import Dict, List, Any, Optional, BinaryIO
import logging
import traceback

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self, aws_access_key: str, aws_secret_key: str, region: str, bucket: str,
                 base_path: str = 'user_data/'):
        logger.info(f"Инициализация S3Service: регион={region}, бакет={bucket}, base_path={base_path}")

        # Проверяем наличие учетных данных
        if not aws_access_key or aws_access_key == "dummy-access-key":
            logger.warning("AWS Access Key не настроен или имеет значение по умолчанию")
        if not aws_secret_key or aws_secret_key == "dummy-secret-key":
            logger.warning("AWS Secret Key не настроен или имеет значение по умолчанию")

        try:
            logger.info("Создание клиента boto3.client('s3')...")
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )
            logger.info("S3 клиент успешно создан")

            # Попытка получить информацию о регионе текущего пользователя
            try:
                sts_client = boto3.client(
                    'sts',
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    region_name=region
                )
                identity = sts_client.get_caller_identity()
                logger.info(
                    f"Успешная аутентификация в AWS: Account={identity.get('Account')}, UserId={identity.get('UserId')}")
            except Exception as e:
                logger.warning(f"Не удалось получить информацию о пользователе AWS: {str(e)}")

            self.bucket = bucket
            self.base_path = base_path
        except NoCredentialsError:
            logger.error("Учетные данные AWS не предоставлены или недействительны")
            raise
        except BotoCoreError as e:
            logger.error(f"Ошибка BotoCore при создании S3 клиента: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при создании S3 клиента: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def upload_file(self, file_data: BinaryIO, file_path: str, content_type: Optional[str] = None) -> Dict:
        """Загружает файл в S3 и возвращает информацию о файле"""
        logger.info(f"Загрузка файла в S3: bucket={self.bucket}, path={file_path}, тип={content_type}")

        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            logger.debug(f"Выполнение upload_fileobj с параметрами: bucket={self.bucket}, key={file_path}")
            self.s3_client.upload_fileobj(
                file_data,
                self.bucket,
                file_path,
                ExtraArgs=extra_args
            )

            logger.info(f"Файл успешно загружен в S3: {file_path}")
            return {
                'bucket': self.bucket,
                'key': file_path,
                'url': f"s3://{self.bucket}/{file_path}"
            }
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Ошибка AWS при загрузке файла: {error_code} - {error_message}")
            logger.error(traceback.format_exc())
            raise
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при загрузке файла: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def get_file(self, file_path: str) -> Dict:
        """Получает файл из S3"""
        logger.info(f"Получение файла из S3: bucket={self.bucket}, path={file_path}")

        try:
            logger.debug(f"Выполнение get_object с параметрами: bucket={self.bucket}, key={file_path}")
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=file_path
            )

            logger.info(f"Файл успешно получен из S3: {file_path}")
            logger.debug(
                f"Метаданные файла: ContentType={response.get('ContentType')}, ContentLength={response.get('ContentLength')}")

            return {
                'body': response['Body'],
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'content_length': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified')
            }
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Ошибка AWS при получении файла: {error_code} - {error_message}")

            # Особая обработка для случая, когда файл не найден
            if error_code == 'NoSuchKey':
                logger.error(f"Файл не найден в S3: {file_path}")

            logger.error(traceback.format_exc())
            raise
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при получении файла: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def delete_file(self, file_path: str) -> bool:
        """Удаляет файл из S3"""
        logger.info(f"Удаление файла из S3: bucket={self.bucket}, path={file_path}")

        try:
            logger.debug(f"Выполнение delete_object с параметрами: bucket={self.bucket}, key={file_path}")
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=file_path
            )
            logger.info(f"Файл успешно удален из S3: {file_path}")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Ошибка AWS при удалении файла: {error_code} - {error_message}")
            logger.error(traceback.format_exc())
            return False
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при удалении файла: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def get_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """Создает временную ссылку для доступа к файлу"""
        logger.info(
            f"Создание presigned URL для файла: bucket={self.bucket}, path={file_path}, expiration={expiration}")

        try:
            logger.debug(f"Выполнение generate_presigned_url с параметрами: bucket={self.bucket}, key={file_path}")
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': file_path
                },
                ExpiresIn=expiration
            )
            logger.info(f"Presigned URL успешно создан для файла: {file_path}")
            return url
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Ошибка AWS при создании presigned URL: {error_code} - {error_message}")
            logger.error(traceback.format_exc())
            raise
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при создании presigned URL: {str(e)}")
            logger.error(traceback.format_exc())
            raise