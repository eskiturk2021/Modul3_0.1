# api_gateway/storage/s3_client.py
import boto3
import os
from botocore.exceptions import ClientError
from typing import Dict, List, Any, Optional, BinaryIO
import logging

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self, aws_access_key: str, aws_secret_key: str, region: str, bucket: str,
                 base_path: str = 'user_data/'):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        self.bucket = bucket
        self.base_path = base_path

    def upload_file(self, file_data: BinaryIO, file_path: str, content_type: Optional[str] = None) -> Dict:
        """Загружает файл в S3 и возвращает информацию о файле"""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.s3_client.upload_fileobj(
                file_data,
                self.bucket,
                file_path,
                ExtraArgs=extra_args
            )

            return {
                'bucket': self.bucket,
                'key': file_path,
                'url': f"s3://{self.bucket}/{file_path}"
            }
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            raise

    def get_file(self, file_path: str) -> Dict:
        """Получает файл из S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=file_path
            )
            return {
                'body': response['Body'],
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'content_length': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified')
            }
        except ClientError as e:
            logger.error(f"Error getting file from S3: {str(e)}")
            raise

    def delete_file(self, file_path: str) -> bool:
        """Удаляет файл из S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=file_path
            )
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            return False

    def get_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """Создает временную ссылку для доступа к файлу"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': file_path
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise