import functools
import io
from typing import Callable

import boto3
import humanize
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from mypy_boto3_s3.client import S3Client
from opentelemetry.trace import Span

from .models import Image


def _traced(span_name: str):
    def decorator(func: Callable[..., object]):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from django_thumbnail.telemetry import get_tracer

            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                return func(*args, span=span, **kwargs)

        return wrapper

    return decorator


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
    @_traced("s3.download")
    def download(bucket: str, key: str, span: Span | None = None) -> io.BytesIO:
        obj = S3.client().get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
        if span:
            span.set_attributes(
                {
                    "bucket": bucket,
                    "key": key,
                    "filename": key.split("/")[-1],
                    "size_bytes": len(body),
                    "readable_size": humanize.naturalsize(len(body)),
                }
            )
        return io.BytesIO(body)

    @staticmethod
    @_traced("s3.upload")
    def upload(
        bucket: str, key: str, data: io.BytesIO, span: Span | None = None
    ) -> None:
        body = data.getvalue()
        if span:
            span.set_attributes(
                {
                    "bucket": bucket,
                    "key": key,
                    "filename": key.split("/")[-1],
                    "size_bytes": len(body),
                    "readable_size": humanize.naturalsize(len(body)),
                }
            )
        S3.client().put_object(Bucket=bucket, Key=key, Body=body)

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
        return S3.client().generate_presigned_url(
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
