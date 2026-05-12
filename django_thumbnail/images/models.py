import io
import uuid
from pathlib import Path

from django.contrib.auth.models import User
from django.db import models


class ImageStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    DONE = "done", "Done"
    FAILED = "failed", "Failed"


class ImageQuerySet(models.QuerySet):
    def for_user(self, user: User) -> "ImageQuerySet":
        return self.filter(user=user)


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="images")
    original_filename = models.CharField(max_length=255)
    original_key = models.CharField(max_length=512)
    thumbnail_key = models.CharField(max_length=512, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ImageQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        ts = self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "?"
        return f"{self.original_filename} ({self.user}) [{ts}]"

    def latest_task(self) -> "ImageTask | None":
        return self.tasks.order_by("-created_at").first()

    def current_status(self) -> str:
        task = self.latest_task()
        return task.status if task else ImageStatus.PENDING

    @staticmethod
    def format_key(user_id: int, image_id: uuid.UUID, filename: str) -> str:
        ext = Path(filename).suffix
        return f"users/{user_id}/{image_id}/{uuid.uuid4().hex}{ext}"

    @staticmethod
    def format_thumbnail_key_from_original(original_key: str) -> str:
        path = Path(original_key)
        stem = path.stem
        return f"{path.parent}/{stem}_thumbnail{path.suffix}"

    @classmethod
    def create_with_key(cls, user: User, filename: str) -> "Image":
        image_id = uuid.uuid4()
        original_key = cls.format_key(user.id, image_id, filename)
        thumbnail_key = cls.format_thumbnail_key_from_original(original_key)

        return cls.objects.create(
            id=image_id,
            user=user,
            original_filename=filename,
            original_key=original_key,
            thumbnail_key=thumbnail_key,
        )

    def upload_original(self, data: io.BytesIO) -> None:
        from django.conf import settings
        from .utils import S3

        S3.upload(settings.AWS_STORAGE_BUCKET_NAME, self.original_key, data)

    def delete_from_storage(self) -> None:
        from django.conf import settings
        from .utils import S3

        for key in [self.original_key, self.thumbnail_key]:
            if key:
                S3.delete(settings.AWS_STORAGE_BUCKET_NAME, key)

    def to_dict(self) -> dict:
        from .utils import S3

        return {
            "id": str(self.id),
            "original_filename": self.original_filename,
            "status": self.current_status(),
            "thumbnail_url": S3.presign_preview_url(self),
            "created_at": self.created_at.isoformat(),
        }


class ImageTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="tasks")
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=ImageStatus.choices, default=ImageStatus.PENDING
    )
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["image", "-created_at"])]

    def __str__(self) -> str:
        ts = self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "?"
        return f"ImageTask({self.image.original_filename}, {self.image.user}, {self.status}) [{ts}]"

    def mark_processing(self, celery_task_id: str) -> None:
        self.status = ImageStatus.PROCESSING
        self.celery_task_id = celery_task_id
        self.save(update_fields=["status", "celery_task_id", "updated_at"])

    def mark_done(self) -> None:
        self.status = ImageStatus.DONE
        self.save(update_fields=["status", "updated_at"])

    def mark_failed(self, error: str) -> None:
        self.status = ImageStatus.FAILED
        self.error_message = error
        self.save(update_fields=["status", "error_message", "updated_at"])

    @classmethod
    def create_and_dispatch(cls, image: "Image") -> "ImageTask":
        from .tasks import generate_thumbnail

        task = cls.objects.create(image=image)
        async_result = generate_thumbnail.delay(str(task.id))
        task.celery_task_id = async_result.id
        task.save(update_fields=["celery_task_id", "updated_at"])
        return task

    def to_dict(self) -> dict:
        from .utils import S3

        return {
            "task_id": str(self.id),
            "celery_task_id": self.celery_task_id,
            "image_id": str(self.image_id),
            "status": self.status,
            "error_message": self.error_message,
            "thumbnail_url": S3.presign_preview_url(self.image)
            if self.status == ImageStatus.DONE
            else None,
        }
