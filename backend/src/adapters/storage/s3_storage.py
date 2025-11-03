"""S3 storage adapter implementation."""

from typing import Optional

import boto3
from botocore.exceptions import ClientError

from config.logging import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class S3StorageAdapter:
    """Adapter for AWS S3 storage."""
    
    def __init__(self):
        settings = get_settings()
        self.bucket_name = settings.s3_bucket_name
        self.region = settings.aws_region
        
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=self.region,
        )
    
    async def put_file(
        self,
        file_data: bytes,
        file_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to S3."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_data,
                ContentType=content_type,
            )
            
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_name}"
            logger.info(f"Uploaded file to S3: {file_name}")
            return url
            
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise
    
    async def get_file(
        self,
        file_name: str,
    ) -> bytes:
        """Download file from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_name,
            )
            return response["Body"].read()
            
        except ClientError as e:
            logger.error(f"S3 download error: {e}")
            raise
    
    async def delete_file(
        self,
        file_name: str,
    ) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_name,
            )
            logger.info(f"Deleted file from S3: {file_name}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 delete error: {e}")
            return False
    
    async def get_presigned_url(
        self,
        file_name: str,
        expiration: int = 3600,
    ) -> str:
        """Generate presigned URL for S3 object."""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": file_name,
                },
                ExpiresIn=expiration,
            )
            return url
            
        except ClientError as e:
            logger.error(f"S3 presigned URL error: {e}")
            raise

