import io
from unittest.mock import patch

import pytest
from PIL import Image as PILImage

from images.models import ImageStatus
from images.tasks import (
    InvalidImageError,
    _create_thumbnail_buffer,
    _validate_image_buffer,
    generate_thumbnail,
)

from .factories import ImageTaskFactory
from .utils import make_image_buf

pytestmark = pytest.mark.django_db


class TestGenerateThumbnail:
    def test_success_marks_done(self):
        task = ImageTaskFactory()
        buf = make_image_buf()
        with (
            patch("images.tasks.S3.download", return_value=buf),
            patch("images.tasks.S3.upload") as mock_upload,
        ):
            generate_thumbnail(str(task.id))
        task.refresh_from_db()
        assert task.status == ImageStatus.DONE
        mock_upload.assert_called_once()

    def test_invalid_image_marks_failed(self):
        task = ImageTaskFactory()
        bad_buf = io.BytesIO(b"not an image")
        with patch("images.tasks.S3.download", return_value=bad_buf):
            generate_thumbnail(str(task.id))
        task.refresh_from_db()
        assert task.status == ImageStatus.FAILED
        assert task.error_message == "invalid image file"

    def test_s3_error_marks_failed(self):
        task = ImageTaskFactory()
        with patch(
            "images.tasks.S3.download", side_effect=Exception("connection refused")
        ):
            with pytest.raises(Exception):
                generate_thumbnail(str(task.id))
        task.refresh_from_db()
        assert task.status == ImageStatus.FAILED

    def test_thumbnail_uploaded_to_correct_key(self):
        task = ImageTaskFactory()
        buf = make_image_buf()
        with (
            patch("images.tasks.S3.download", return_value=buf),
            patch("images.tasks.S3.upload") as mock_upload,
        ):
            generate_thumbnail(str(task.id))
        args = mock_upload.call_args[0]
        assert args[1] == task.image.thumbnail_key


class TestValidateImageBuffer:
    def test_valid_image_passes(self):
        _validate_image_buffer(make_image_buf())

    def test_invalid_bytes_raises(self):
        with pytest.raises(InvalidImageError):
            _validate_image_buffer(io.BytesIO(b"garbage"))


class TestCreateThumbnailBuffer:
    def test_output_is_jpeg(self):
        out = _create_thumbnail_buffer(make_image_buf())
        img = PILImage.open(out)
        assert img.format == "JPEG"

    def test_respects_thumbnail_size(self):
        from images.tasks import THUMBNAIL_SIZE

        out = _create_thumbnail_buffer(make_image_buf(size=(500, 500)))
        img = PILImage.open(out)
        assert img.size == THUMBNAIL_SIZE
