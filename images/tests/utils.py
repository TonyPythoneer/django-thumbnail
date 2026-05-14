import io

from PIL import Image as PILImage


def make_image_buf(size: tuple[int, int] = (100, 100), fmt: str = "JPEG") -> io.BytesIO:
    buf = io.BytesIO()
    PILImage.new("RGB", size, (0, 128, 255)).save(buf, format=fmt)
    buf.seek(0)
    return buf
