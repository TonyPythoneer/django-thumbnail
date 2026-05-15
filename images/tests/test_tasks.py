import io
from unittest.mock import patch

import pytest
from celery.exceptions import Retry

from images.models import ImageStatus
from images.tasks import generate_thumbnail

from .factories import ImageTaskFactory
from .utils import make_image_buf

pytestmark = pytest.mark.django_db


class TestGenerateThumbnail:
    def test_success_marks_done(self):
        task = ImageTaskFactory()
        buf = make_image_buf()
        with (
            patch("images.tasks.internal_s3.download", return_value=buf),
            patch("images.tasks.internal_s3.upload") as mock_upload,
        ):
            generate_thumbnail(str(task.id))
        task.refresh_from_db()
        assert task.status == ImageStatus.DONE
        mock_upload.assert_called_once()

    def test_invalid_image_marks_failed(self):
        task = ImageTaskFactory()
        bad_buf = io.BytesIO(b"not an image")
        with patch("images.tasks.internal_s3.download", return_value=bad_buf):
            generate_thumbnail(str(task.id))
        task.refresh_from_db()
        assert task.status == ImageStatus.FAILED
        assert task.error_message == "invalid image file"

    def test_s3_error_marks_failed_after_exhausting_retries(self):
        task = ImageTaskFactory()
        with (
            patch(
                "images.tasks.internal_s3.download",
                side_effect=ConnectionError("connection refused"),
            ),
            pytest.raises(ConnectionError),
        ):
            generate_thumbnail.apply(args=[str(task.id)], retries=generate_thumbnail.max_retries)
        task.refresh_from_db()
        assert task.status == ImageStatus.FAILED

    def test_s3_error_stays_processing_during_retry(self):
        task = ImageTaskFactory()
        with (
            patch(
                "images.tasks.internal_s3.download",
                side_effect=ConnectionError("connection refused"),
            ),
            pytest.raises(Retry),
        ):
            generate_thumbnail.apply(
                args=[str(task.id)], retries=generate_thumbnail.max_retries - 1
            )
        task.refresh_from_db()
        assert task.status == ImageStatus.PROCESSING

    def test_thumbnail_uploaded_to_correct_key(self):
        task = ImageTaskFactory()
        buf = make_image_buf()
        with (
            patch("images.tasks.internal_s3.download", return_value=buf),
            patch("images.tasks.internal_s3.upload") as mock_upload,
        ):
            generate_thumbnail(str(task.id))
        args = mock_upload.call_args[0]
        assert args[1] == task.image.thumbnail_key
