import io
import time
from pathlib import Path

import boto3
import psutil
from celery import shared_task
from django.conf import settings
from PIL import Image as PillowImage

from .models import Image, ImageTask, ImageStatus

THUMBNAIL_SIZE = (300, 300)


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _download(s3, bucket: str, key: str) -> io.BytesIO:
    from django_thumbnail.telemetry import get_tracer
    tracer = get_tracer()
    with tracer.start_as_current_span("minio.download") as span:
        span.set_attribute("bucket", bucket)
        span.set_attribute("key", key)
        buf = io.BytesIO()
        s3.download_fileobj(bucket, key, buf)
        span.set_attribute("size_bytes", buf.tell())
        buf.seek(0)
        return buf


def _upload(s3, bucket: str, key: str, data: io.BytesIO) -> None:
    from django_thumbnail.telemetry import get_tracer
    tracer = get_tracer()
    with tracer.start_as_current_span("minio.upload") as span:
        span.set_attribute("bucket", bucket)
        span.set_attribute("key", key)
        size = data.seek(0, 2)
        data.seek(0)
        span.set_attribute("size_bytes", size)
        s3.upload_fileobj(data, bucket, key)


@shared_task(bind=True, max_retries=3)
def generate_thumbnail(self, image_task_id: str) -> None:
    from django_thumbnail.telemetry import get_tracer
    tracer = get_tracer()

    start = time.perf_counter()
    proc = psutil.Process()

    task = ImageTask.objects.select_related("image").get(id=image_task_id)
    task.mark_processing(self.request.id)
    image = task.image
    s3 = _s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME

    with tracer.start_as_current_span("celery.task.generate_thumbnail") as span:
        span.set_attribute("task_id", self.request.id or "")
        span.set_attribute("image_task_id", image_task_id)
        span.set_attribute("image_id", str(image.id))
        span.set_attribute("user_id", str(image.user_id))
        span.set_attribute("image_name", image.original_filename)

        try:
            buf = _download(s3, bucket, image.original_key)

            with PillowImage.open(buf) as img:
                img.thumbnail(THUMBNAIL_SIZE)
                out = io.BytesIO()
                fmt = img.format or "JPEG"
                img.save(out, format=fmt)
                out.seek(0)

            stem = Path(image.original_key).stem
            suffix = Path(image.original_key).suffix
            thumbnail_key = f"{stem}_thumbnail{suffix}"

            _upload(s3, bucket, thumbnail_key, out)

            image.thumbnail_key = thumbnail_key
            image.save(update_fields=["thumbnail_key"])
            task.mark_done()

            duration_ms = int((time.perf_counter() - start) * 1000)
            span.set_attribute("status", "done")
            span.set_attribute("duration_ms", duration_ms)
            span.set_attribute("cpu_percent", proc.cpu_percent(interval=0.1))
            span.set_attribute("memory_mb", proc.memory_info().rss / 1024 / 1024)

        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            span.set_attribute("status", "failed")
            span.set_attribute("duration_ms", duration_ms)
            span.set_attribute("cpu_percent", proc.cpu_percent(interval=0.1))
            span.set_attribute("memory_mb", proc.memory_info().rss / 1024 / 1024)
            span.record_exception(exc)

            task.mark_failed(str(exc))
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
