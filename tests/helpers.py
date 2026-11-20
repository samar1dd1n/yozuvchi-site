import shutil
import tempfile
from io import BytesIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from pypdf import PdfWriter


def make_image(name="cover.png", size=(500, 700), color=(120, 40, 30), left_color=None):
    img = Image.new("RGB", size, color)
    if left_color:
        img.paste(left_color, (0, 0, max(1, size[0] // 10), size[1]))
    buffer = BytesIO()
    img.save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def make_pdf(name="page.pdf", pages=1):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(595, 842)
    buffer = BytesIO()
    writer.write(buffer)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="application/pdf")


class MediaTestCase(TestCase):
    """Har bir test sinfi uchun alohida vaqtinchalik media papka."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls._override = override_settings(
            MEDIA_ROOT=cls._tmp,
            PDF_CACHE_DIR=str(Path(cls._tmp) / "pdf_cache"),
        )
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def make_staff(self, username="admin", password="kuchli-parol-123"):
        return get_user_model().objects.create_user(username=username, password=password, is_staff=True)
