import io
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from django.conf import settings
from django.http import HttpRequest, JsonResponse

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


class _S3BaseClient:
    AWS_S3_ENDPOINT_URL = settings.AWS_S3_ENDPOINT_URL

    AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
    AWS_CONFIG = None

    def __init__(self):
        self._client: "S3Client" = boto3.client(
            "s3",
            endpoint_url=self.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=self.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
            config=self.AWS_CONFIG,
        )


class InternalS3(_S3BaseClient):
    def download(self, bucket: str, key: str) -> io.BytesIO:
        obj = self._client.get_object(Bucket=bucket, Key=key)
        return io.BytesIO(obj["Body"].read())

    def upload(self, bucket: str, key: str, data: io.BytesIO) -> None:
        self._client.put_object(Bucket=bucket, Key=key, Body=data.getvalue())

    def delete(self, bucket: str, key: str) -> None:
        self._client.delete_object(Bucket=bucket, Key=key)


class PublicS3(_S3BaseClient):
    AWS_S3_ENDPOINT_URL = settings.AWS_S3_PUBLIC_ENDPOINT_URL

    AWS_CONFIG = Config(signature_version=settings.AWS_S3_PUBLIC_SIGNATURE_VERSION)

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


def login_required_json(view):
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "auth required"}, status=401)
        return view(request, *args, **kwargs)

    return wrapper
