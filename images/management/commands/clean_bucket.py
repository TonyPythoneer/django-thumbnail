import boto3
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.functional import cached_property


class Command(BaseCommand):
    help = "Clear all objects from MinIO bucket"

    @cached_property
    def s3(self):
        return boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    def handle(self, *args, **options):
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        resp = self.s3.list_objects_v2(Bucket=bucket)

        count = 0
        if "Contents" in resp:
            for obj in resp["Contents"]:
                self.s3.delete_object(Bucket=bucket, Key=obj["Key"])
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"✓ Cleared bucket ({count} objects deleted)")
        )
