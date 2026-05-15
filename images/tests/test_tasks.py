import io
from collections.abc import Callable
from unittest.mock import patch

import pytest
from celery.exceptions import Retry

from images.models import ImageStatus
from images.tasks import generate_thumbnail

from .factories import make_image_task
from .utils import make_image_buf

pytestmark = pytest.mark.django_db

MAX_RETRIES = generate_thumbnail.max_retries


class TestGenerateThumbnail:
    @pytest.mark.parametrize(
        ("download_factory", "retries", "expected_status", "expected_error", "expected_raises"),
        [
            (
                lambda: {"return_value": make_image_buf()},
                None,
                ImageStatus.DONE,
                "",
                None,
            ),
            (
                lambda: {"return_value": io.BytesIO(b"not an image")},
                None,
                ImageStatus.FAILED,
                "invalid image file",
                None,
            ),
            (
                lambda: {"side_effect": ConnectionError("connection refused")},
                MAX_RETRIES,
                ImageStatus.FAILED,
                "",
                ConnectionError,
            ),
            (
                lambda: {"side_effect": ConnectionError("connection refused")},
                MAX_RETRIES - 1,
                ImageStatus.PROCESSING,
                "",
                Retry,
            ),
        ],
        ids=["success", "invalid_image", "retry_exhausted", "retry_pending"],
    )
    def test_status_outcomes(
        self,
        download_factory: Callable[[], dict[str, object]],
        retries: int | None,
        expected_status: ImageStatus,
        expected_error: str,
        expected_raises: type[Exception] | None,
    ) -> None:
        task = make_image_task()
        with (
            patch("images.tasks.internal_s3.download", **download_factory()),
            patch("images.tasks.internal_s3.upload"),
        ):
            if expected_raises is not None:
                with pytest.raises(expected_raises):
                    generate_thumbnail.apply(args=[str(task.id)], retries=retries)
            elif retries is not None:
                generate_thumbnail.apply(args=[str(task.id)], retries=retries)
            else:
                generate_thumbnail(str(task.id))

        task.refresh_from_db()
        assert task.status == expected_status
        if expected_error:
            assert task.error_message == expected_error

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
