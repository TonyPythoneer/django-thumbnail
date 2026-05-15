from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.functional import cached_property

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


class Command(BaseCommand):
    help = "Create MinIO bucket if it does not exist"

    @cached_property
    def s3(self) -> S3Client:
        return boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    def handle(self, *args: object, **options: object) -> None:
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        try:
            self.s3.head_bucket(Bucket=bucket)
            self.stdout.write(f"bucket already exists: {bucket}")
        except ClientError:
            self.s3.create_bucket(Bucket=bucket)
            self.stdout.write(f"created bucket: {bucket}")
