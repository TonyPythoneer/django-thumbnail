import io
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from django.conf import settings

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


class _S3BaseClient:
    def __init__(self, endpoint_url: str, config: Config | None = None):
        self._client: S3Client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=config,
        )


class InternalS3(_S3BaseClient):
    def __init__(self):
        super().__init__(endpoint_url=settings.AWS_S3_ENDPOINT_URL)

    def download(self, bucket: str, key: str) -> io.BytesIO:
        obj = self._client.get_object(Bucket=bucket, Key=key)
        return io.BytesIO(obj["Body"].read())

    def upload(self, bucket: str, key: str, data: io.BytesIO) -> None:
        self._client.put_object(Bucket=bucket, Key=key, Body=data.getvalue())

    def delete(self, bucket: str, key: str) -> None:
        self._client.delete_object(Bucket=bucket, Key=key)


class PublicS3(_S3BaseClient):
    def __init__(self):
        super().__init__(
            endpoint_url=settings.AWS_S3_PUBLIC_ENDPOINT_URL,
            config=Config(signature_version=settings.AWS_S3_PUBLIC_SIGNATURE_VERSION),
        )

    _PRESIGN_EXPIRES_IN = 3600

    def presign_get(self, key: str) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": key},
            ExpiresIn=self._PRESIGN_EXPIRES_IN,
        )

    def presign_put(self, key: str) -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": key},
            ExpiresIn=self._PRESIGN_EXPIRES_IN,
        )


internal_s3 = InternalS3()
public_s3 = PublicS3()
