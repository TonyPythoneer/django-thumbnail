import io
from enum import StrEnum
from typing import TYPE_CHECKING

from celery import shared_task
from django.conf import settings
from opentelemetry import trace
from PIL import Image as PillowImage

from .utils import internal_s3

if TYPE_CHECKING:
    from .models import Image

THUMBNAIL_SIZE = (20, 20)


class InvalidImageError(Exception):
    pass


class Outcome(StrEnum):
    DONE = "done"
    INVALID = "invalid"
    RETRY = "retry"
    FAIL = "fail"


def _process_thumbnail(bucket: str, image: Image) -> None:
    buf = internal_s3.download(bucket, image.original_key)
    _validate_image_buffer(buf)
    out = _create_thumbnail_buffer(buf)
    internal_s3.upload(bucket, image.thumbnail_key, out)


def _validate_image_buffer(buf: io.BytesIO) -> None:
    try:
        with PillowImage.open(buf) as img:
            img.verify()
        buf.seek(0)
    except Exception as e:
        raise InvalidImageError("invalid image file") from e


def _create_thumbnail_buffer(original_buffer: io.BytesIO) -> io.BytesIO:
    with PillowImage.open(original_buffer) as img:
        img.thumbnail(THUMBNAIL_SIZE)
        out = io.BytesIO()
        img.save(out, format=img.format)
        out.seek(0)
    return out


@shared_task(bind=True, max_retries=3)
def generate_thumbnail(self, image_task_id: str) -> None:
    from .models import ImageTask

    task = ImageTask.objects.select_related("image").get(id=image_task_id)
    celery_id = self.request.id or ""
    task.mark_processing(celery_id)

    # tracing
    span = trace.get_current_span()
    span_attributes = {
        "task_id": celery_id,
        "image_task_id": image_task_id,
        "image_id": str(task.image.id),
        "user_id": str(task.image.user_id),
        "image_name": task.image.original_filename,
    }

    try:
        _process_thumbnail(settings.AWS_STORAGE_BUCKET_NAME, task.image)
        task.mark_done()
        span_attributes["status"] = Outcome.DONE
    except InvalidImageError:
        task.mark_failed("invalid image file")
        span_attributes["status"] = Outcome.INVALID
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            task.mark_failed(str(exc))
            span_attributes["status"] = Outcome.FAIL
        else:
            span_attributes["status"] = Outcome.RETRY
        span.record_exception(exc)
        raise self.retry(exc=exc, countdown=2**self.request.retries)
    finally:
        span.set_attributes(span_attributes)
