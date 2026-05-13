import io

import pytest
from PIL import Image as PILImage

from images.tasks import (
    InvalidImageError,
    _create_thumbnail_buffer,
    _validate_image_buffer,
)

from .utils import make_image_buf


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
