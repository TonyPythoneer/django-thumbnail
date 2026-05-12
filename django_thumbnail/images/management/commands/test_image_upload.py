import json
import tempfile
import urllib.request
from http import HTTPMethod
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from PIL import Image as PILImage

from images.models import Image, ImageTask
from images.tasks import generate_thumbnail
from images.utils import S3


class Command(BaseCommand):
    help = "Run smoke test: create image record, upload, create task, check status"

    def _create_test_image(self) -> str:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        path = f.name
        f.close()
        PILImage.new("RGB", (200, 200), (0, 128, 255)).save(path)
        return path

    def handle(self, *args, **options):
        test_image_path = self._create_test_image()

        try:
            # Get user directly
            self.stdout.write("--- get user ---")
            user = User.objects.get(username="test1@example.com")
            self.stdout.write(f"user: {user.username}")

            # Create image record + presigned upload URL
            self.stdout.write("--- create image record ---")
            image = Image.create_with_key(user, "smoke.jpg")
            upload_url = S3.presign_upload_url(image)
            self.stdout.write(
                json.dumps(
                    {"image_id": str(image.id), "upload_url": upload_url}, indent=2
                )
            )

            # Upload to MinIO via presigned URL (requires real HTTP)
            self.stdout.write("--- upload to MinIO via signed URL ---")
            image_bytes = Path(test_image_path).read_bytes()
            req = urllib.request.Request(
                upload_url,
                data=image_bytes,
                method=HTTPMethod.PUT,
                headers={"Content-Type": ""},
            )
            with urllib.request.urlopen(req) as r:
                self.stdout.write(self.style.SUCCESS(f"✓ uploaded (status {r.status})"))

            # Create task + dispatch Celery
            self.stdout.write("--- create task ---")
            task = ImageTask.objects.create(image=image)
            async_result = generate_thumbnail.delay(str(task.id))
            task.celery_task_id = async_result.id
            task.save(update_fields=["celery_task_id", "updated_at"])
            self.stdout.write(json.dumps(task.to_dict(), indent=2))
        finally:
            Path(test_image_path).unlink(missing_ok=True)
