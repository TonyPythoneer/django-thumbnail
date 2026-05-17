import io
from collections.abc import Callable
from typing import cast
from unittest.mock import patch

import pytest
from celery.exceptions import Retry

from images.models import ImageStatus
from images.tasks import GENERATE_THUMBNAIL_MAX_RETRIES, generate_thumbnail

from .factories import make_image_task
from .utils import make_image_buf

pytestmark = pytest.mark.django_db

MAX_RETRIES = GENERATE_THUMBNAIL_MAX_RETRIES
_apply: Callable[..., object] = cast(Callable[..., object], generate_thumbnail.apply)


class TestGenerateThumbnail:
    @pytest.mark.parametrize(
        ("download_return", "expected_status", "expected_error"),
        [
            pytest.param(
                lambda: make_image_buf(),
                ImageStatus.DONE,
                "",
                id="success",
            ),
            pytest.param(
                lambda: io.BytesIO(b"not an image"),
                ImageStatus.FAILED,
                "invalid image file",
                id="invalid_image",
            ),
        ],
    )
    def test_direct_call(
        self,
        download_return: Callable[[], object],
        expected_status: ImageStatus,
        expected_error: str,
    ) -> None:
        task = make_image_task()
        with (
            patch("images.tasks.internal_s3.download", return_value=download_return()),
            patch("images.tasks.internal_s3.upload"),
        ):
            generate_thumbnail(str(task.id))

        task.refresh_from_db()
        assert task.status == expected_status
        assert task.error_message == expected_error

    @pytest.mark.parametrize(
        ("retries", "expected_status", "expected_raises"),
        [
            pytest.param(
                MAX_RETRIES,
                ImageStatus.FAILED,
                ConnectionError,
                id="retry_exhausted",
            ),
            pytest.param(
                MAX_RETRIES - 1,
                ImageStatus.PROCESSING,
                Retry,
                id="retry_pending",
            ),
        ],
    )
    def test_resilient_to_download_failure(
        self,
        retries: int,
        expected_status: ImageStatus,
        expected_raises: type[Exception],
    ) -> None:
        task = make_image_task()
        with (
            patch(
                "images.tasks.internal_s3.download",
                side_effect=ConnectionError("connection refused"),
            ),
            patch("images.tasks.internal_s3.upload"),
            pytest.raises(expected_raises),
        ):
            _apply(args=[str(task.id)], retries=retries)

        task.refresh_from_db()
        assert task.status == expected_status

    def test_thumbnail_uploaded_to_correct_key(self) -> None:
        task = make_image_task()
        buf = make_image_buf()
        with (
            patch("images.tasks.internal_s3.download", return_value=buf),
            patch("images.tasks.internal_s3.upload") as mock_upload,
        ):
            generate_thumbnail(str(task.id))
        args = mock_upload.call_args[0]
        assert args[1] == task.image.thumbnail_key
