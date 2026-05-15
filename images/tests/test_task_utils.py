import io

import pytest
from PIL import Image as PILImage

from images.tasks import InvalidImageError, _make_thumbnail

from .utils import make_image_buf


class TestMakeThumbnail:
    def test_output_is_jpeg(self):
        out = _make_thumbnail(make_image_buf())
        img = PILImage.open(out)
        assert img.format == "JPEG"

    def test_respects_thumbnail_size(self):
        from images.tasks import THUMBNAIL_SIZE

        out = _make_thumbnail(make_image_buf(size=(500, 500)))
        img = PILImage.open(out)
        assert img.size == THUMBNAIL_SIZE

    def test_invalid_bytes_raises(self):
        with pytest.raises(InvalidImageError):
            _make_thumbnail(io.BytesIO(b"garbage"))
