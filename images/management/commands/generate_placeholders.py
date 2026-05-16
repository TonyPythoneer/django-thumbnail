from pathlib import Path

from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

PLACEHOLDERS = [
    ("placeholder_small.jpg", 400, 300, "#4A90D9"),
    ("placeholder_medium.jpg", 800, 600, "#7B68EE"),
    ("placeholder_large.jpg", 1920, 1080, "#50C878"),
]

OUT_DIR = Path(__file__).resolve().parents[3] / "static" / "images" / "placeholders"


class Command(BaseCommand):
    help = "Generate placeholder images for upload demo"

    def handle(self, *args: object, **options: object) -> None:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for filename, w, h, color in PLACEHOLDERS:
            img = Image.new("RGB", (w, h), color)
            draw = ImageDraw.Draw(img)
            label = f"{w}x{h}"
            font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), label, font=font)
            x = (w - (bbox[2] - bbox[0])) // 2
            y = (h - (bbox[3] - bbox[1])) // 2
            draw.text((x, y), label, fill="white", font=font)
            out_path = OUT_DIR / filename
            img.save(out_path, "JPEG", quality=85)
            self.stdout.write(f"generated: {out_path}")
