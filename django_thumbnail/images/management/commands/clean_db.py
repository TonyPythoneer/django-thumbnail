from django.core.management.base import BaseCommand
from images.models import Image, ImageTask


class Command(BaseCommand):
    help = "Clear all images and tasks from database"

    def handle(self, *args, **options):
        img_count = Image.objects.count()
        task_count = ImageTask.objects.count()

        Image.objects.all().delete()
        ImageTask.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Cleared {img_count} images, {task_count} tasks"
            )
        )
