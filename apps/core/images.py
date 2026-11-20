"""Yuklangan rasmlarni qayta ishlash: telefon EXIF burilishini tuzatish,
o'lchamni kichraytirish, siqish, thumbnail va kitob qirrasi rangi."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


@dataclass
class ProcessedImage:
    content: ContentFile
    width: int
    height: int
    image: Image.Image


def _has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)


def _open(file) -> Image.Image:
    file.seek(0)
    img = Image.open(file)
    img.load()
    file.seek(0)
    return ImageOps.exif_transpose(img)


def optimize_image(file, max_side: int, quality: int = 86) -> ProcessedImage:
    img = _open(file)
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    stem = Path(getattr(file, "name", "") or "image").stem or "image"
    buffer = BytesIO()
    if _has_alpha(img):
        img = img.convert("RGBA")
        img.save(buffer, "PNG", optimize=True)
        ext = ".png"
    else:
        img = img.convert("RGB")
        img.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
        ext = ".jpg"
    return ProcessedImage(ContentFile(buffer.getvalue(), name=f"{stem}{ext}"), img.width, img.height, img)


def make_thumbnail(img: Image.Image, width: int = 480) -> ContentFile:
    thumb = img.copy()
    thumb.thumbnail((width, width * 3), Image.Resampling.LANCZOS)
    if _has_alpha(thumb):
        background = Image.new("RGB", thumb.size, (255, 255, 255))
        background.paste(thumb.convert("RGBA"), mask=thumb.convert("RGBA").getchannel("A"))
        thumb = background
    buffer = BytesIO()
    thumb.convert("RGB").save(buffer, "JPEG", quality=80, optimize=True)
    return ContentFile(buffer.getvalue(), name="thumb.jpg")


def edge_color(img: Image.Image, fraction: float = 0.06, darken: float = 0.82) -> str:
    """Muqovaning chap chetidagi o'rtacha rangni biroz to'qlashtirib qaytaradi —
    kitob qirrasi muqovaning davomi bo'lib ko'rinadi."""
    rgb = img.convert("RGB")
    strip_width = max(1, int(rgb.width * fraction))
    strip = rgb.crop((0, 0, strip_width, rgb.height)).resize((1, 1), Image.Resampling.BOX)
    r, g, b = strip.getpixel((0, 0))
    return "#{:02x}{:02x}{:02x}".format(int(r * darken), int(g * darken), int(b * darken))


def readable_ink(hex_color: str) -> str:
    """Berilgan fon ustida o'qiladigan matn rangi (oq yoki qora)."""
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))

    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    luminance = 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
    return "#1B1A17" if luminance > 0.4 else "#FBF7EF"
