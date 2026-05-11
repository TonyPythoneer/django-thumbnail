from django.conf import settings
from django.core.management.base import BaseCommand
import boto3
from botocore.exceptions import ClientError


class Command(BaseCommand):
    help = "Create MinIO bucket if it does not exist"

    def handle(self, *args, **options):
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        try:
            s3.head_bucket(Bucket=bucket)
            self.stdout.write(f"bucket already exists: {bucket}")
        except ClientError:
            s3.create_bucket(Bucket=bucket)
            self.stdout.write(f"created bucket: {bucket}")
