import uuid
from django.db import models
from django.contrib.auth.models import User


class ImageStatus(models.TextChoices):
    PENDING    = "pending",    "Pending"
    PROCESSING = "processing", "Processing"
    DONE       = "done",       "Done"
    FAILED     = "failed",     "Failed"


class SizeVariant(models.TextChoices):
    SMALL  = "small",  "Small"
    MEDIUM = "medium", "Medium"
    LARGE  = "large",  "Large"
    CUSTOM = "custom", "Custom"


class ImageQuerySet(models.QuerySet):
    def for_user(self, user: User) -> "ImageQuerySet":
        return self.filter(user=user)


class Image(models.Model):
    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name="images")
    original_filename = models.CharField(max_length=255)
    original_key      = models.CharField(max_length=512)
    thumbnail_key     = models.CharField(max_length=512, blank=True, default="")
    size_variant      = models.CharField(max_length=10, choices=SizeVariant.choices)
    file_size         = models.BigIntegerField(default=0)
    created_at        = models.DateTimeField(auto_now_add=True)

    objects = ImageQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.user})"

    def latest_task(self) -> "ImageTask | None":
        return self.tasks.order_by("-created_at").first()

    def current_status(self) -> str:
        task = self.latest_task()
        return task.status if task else ImageStatus.PENDING


class ImageTask(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image          = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="tasks")
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    status         = models.CharField(max_length=20, choices=ImageStatus.choices,
                                      default=ImageStatus.PENDING)
    error_message  = models.TextField(blank=True, default="")
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["image", "-created_at"])]

    def __str__(self) -> str:
        return f"ImageTask({self.image.original_filename}, {self.status})"

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
