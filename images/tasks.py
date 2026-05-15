import io
from enum import StrEnum

from celery import Task, shared_task
from django.conf import settings
from opentelemetry import trace
from PIL import Image as PillowImage

from .models import Image, ImageTask
from .storage import internal_s3

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
    out = _make_thumbnail(buf)
    internal_s3.upload(bucket, image.thumbnail_key, out)


def _make_thumbnail(buf: io.BytesIO) -> io.BytesIO:
    # thumbnail() decodes the file, so verify() would be redundant.
    # Invalid bytes surface as UnidentifiedImageError/OSError.
    try:
        with PillowImage.open(buf) as img:
            img.thumbnail(THUMBNAIL_SIZE)
            out = io.BytesIO()
            img.save(out, format=img.format)
    except (PillowImage.UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("invalid image file") from exc
    out.seek(0)
    return out


@shared_task(bind=True, max_retries=3)
def generate_thumbnail(self: Task, image_task_id: str) -> None:
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
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
    finally:
        span.set_attributes(span_attributes)
