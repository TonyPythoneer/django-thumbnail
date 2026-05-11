import io
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


@shared_task(bind=True, max_retries=3)
def generate_thumbnail(self, image_task_id: str) -> None:
    import time
    start = time.perf_counter()

    task = ImageTask.objects.select_related("image").get(id=image_task_id)
    task.mark_processing(self.request.id)

    image = task.image
    s3 = _s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME

    try:
        # download original
        buf = io.BytesIO()
        s3.download_fileobj(bucket, image.original_key, buf)
        buf.seek(0)

        # generate thumbnail
        with PillowImage.open(buf) as img:
            img.thumbnail(THUMBNAIL_SIZE)
            out = io.BytesIO()
            fmt = img.format or "JPEG"
            img.save(out, format=fmt)
            out.seek(0)

        # build thumbnail key
        stem = Path(image.original_key).stem
        suffix = Path(image.original_key).suffix
        thumbnail_key = f"{stem}_thumbnail{suffix}"

        # upload thumbnail
        s3.upload_fileobj(out, bucket, thumbnail_key)

        image.thumbnail_key = thumbnail_key
        image.save(update_fields=["thumbnail_key"])
        task.mark_done()

    except Exception as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        proc = psutil.Process()
        cpu = proc.cpu_percent(interval=0.1)
        mem_mb = proc.memory_info().rss / 1024 / 1024

        task.mark_failed(str(exc))

        raise self.retry(
            exc=exc,
            countdown=2 ** self.request.retries,
        )
