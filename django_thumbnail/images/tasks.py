import io
from enum import StrEnum

from celery import shared_task
from django.conf import settings
from django_thumbnail.telemetry import get_tracer
from PIL import Image as PillowImage

from .models import Image, ImageTask
from .utils import S3

THUMBNAIL_SIZE = (20, 20)


class InvalidImageError(Exception):
    pass


class Outcome(StrEnum):
    DONE = "done"
    INVALID = "invalid"
    RETRY = "retry"


def _process_thumbnail(bucket: str, image: Image) -> None:
    buf = S3.download(bucket, image.original_key)
    _validate_image_buffer(buf)
    out = _create_thumbnail_buffer(buf)
    S3.upload(bucket, image.thumbnail_key, out)


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
    with get_tracer().start_as_current_span(
        "celery.task.generate_thumbnail",
        attributes={"task_id": self.request.id or "", "image_task_id": image_task_id},
    ) as span:
        task = ImageTask.objects.select_related("image").get(id=image_task_id)
        task.mark_processing(self.request.id or "")
        span.set_attributes(
            {
                "image_id": str(task.image.id),
                "user_id": str(task.image.user_id),
                "image_name": task.image.original_filename,
            }
        )

        try:
            _process_thumbnail(settings.AWS_STORAGE_BUCKET_NAME, task.image)
            task.mark_done()
            span.set_attribute("status", Outcome.DONE)
        except InvalidImageError:
            task.mark_failed("invalid image file")
            span.set_attribute("status", Outcome.INVALID)
        except Exception as exc:
            task.mark_failed(str(exc))
            span.set_attribute("status", Outcome.RETRY)
            raise self.retry(exc=exc, countdown=2**self.request.retries)
