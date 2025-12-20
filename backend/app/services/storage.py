import aioboto3
from typing import BinaryIO
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    def __init__(self) -> None:
        self.session = aioboto3.Session()
        self.bucket_name = settings.s3_bucket_name
        self.endpoint_url = settings.aws_endpoint_url if settings.use_minio else None

    async def upload_pdf(self, file_content: bytes, file_key: str) -> str:
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        ) as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content,
                ContentType="application/pdf",
            )
            await logger.ainfo("pdf_uploaded", file_key=file_key, bucket=self.bucket_name)
            return file_key

    async def get_pdf_url(self, file_key: str, expires_in: int = 3600) -> str:
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        ) as s3:
            url = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_key},
                ExpiresIn=expires_in,
            )
            return url

    async def store_artifact(self, file_content: bytes, file_key: str, content_type: str) -> str:
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        ) as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content,
                ContentType=content_type,
            )
            await logger.ainfo("artifact_stored", file_key=file_key, content_type=content_type)
            return file_key

    async def download_file(self, file_key: str) -> bytes:
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        ) as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=file_key)
            async with response["Body"] as stream:
                content = await stream.read()
                return content


storage_service = StorageService()
