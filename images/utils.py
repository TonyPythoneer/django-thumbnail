import io
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from django.conf import settings
from django.http import HttpRequest, JsonResponse

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from .models import Image


class S3:
    _CLIENT_SETTINGS = {
        "endpoint_url": settings.AWS_S3_ENDPOINT_URL,
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
    }
    _PRESIGN_EXPIRES_IN = 3600

    @staticmethod
    def client() -> S3Client:
        return boto3.client("s3", **S3._CLIENT_SETTINGS)

    @staticmethod
    def download(bucket: str, key: str) -> io.BytesIO:
        obj = S3.client().get_object(Bucket=bucket, Key=key)
        return io.BytesIO(obj["Body"].read())

    @staticmethod
    def upload(bucket: str, key: str, data: io.BytesIO) -> None:
        S3.client().put_object(Bucket=bucket, Key=key, Body=data.getvalue())

    @staticmethod
    def delete(bucket: str, key: str) -> None:
        S3.client().delete_object(Bucket=bucket, Key=key)

    @staticmethod
    def presign_preview_url(image: Image) -> str | None:
        if not image.thumbnail_key:
            return None
        return S3._presign_url(image.thumbnail_key, "get_object")

    @staticmethod
    def presign_upload_url(image: Image) -> str:
        return S3._presign_url(image.original_key, "put_object")

    @staticmethod
    def _presign_url(key: str, action: str) -> str:
        sig_version = getattr(settings, "AWS_S3_SIGNATURE_VERSION", None)
        client = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_PUBLIC_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version=sig_version) if sig_version else None,
        )
        return client.generate_presigned_url(
            action,
            Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": key},
            ExpiresIn=S3._PRESIGN_EXPIRES_IN,
        )


def login_required_json(view):
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "auth required"}, status=401)
        return view(request, *args, **kwargs)

    return wrapper
