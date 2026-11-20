import hashlib
import logging
import os
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.db import transaction
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter

from apps.author.models import AuthorProfile
from apps.core.images import make_thumbnail, optimize_image
from apps.core.validators import open_pdf

from .models import Book, BookPage
from .selectors import open_pages

logger = logging.getLogger(__name__)

A4_WIDTH_INCH = 8.27


# ---------- Sahifa yuklash ----------

def render_pdf_thumbnail(data: bytes, width: int = 480):
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(data)
        try:
            page = pdf[0]
            bitmap = page.render(scale=width / page.get_width())
            image = bitmap.to_pil()
        finally:
            pdf.close()
        return make_thumbnail(image, width)
    except Exception:
        logger.warning("PDF thumbnail yasab bo'lmadi", exc_info=True)
        return None


def prepare_page_upload(page: BookPage) -> None:
    """Yangi yuklangan fayl turini aniqlaydi, rasmni siqadi, thumbnail yasaydi."""
    upload = page.file
    if (upload.name or "").lower().endswith(".pdf"):
        upload.seek(0)
        data = upload.read()
        upload.seek(0)
        page.kind = BookPage.Kind.PDF
        page.pdf_page_count = len(open_pdf(BytesIO(data)).pages)
        page.thumbnail = render_pdf_thumbnail(data)
    else:
        processed = optimize_image(upload, max_side=2400)
        page.file = processed.content
        page.kind = BookPage.Kind.IMAGE
        page.pdf_page_count = 1
        page.thumbnail = make_thumbnail(processed.image)


@transaction.atomic
def create_pages_bulk(*, book: Book, files, start_number: int, start_at, interval_days: int) -> list[BookPage]:
    """Ko'p faylni ketma-ket raqam va ochilish sanasi bilan saqlaydi.

    Masalan interval_days=1: 1-sahifa start_at da, 2-sahifa ertasiga, ...
    """
    pages = []
    for index, upload in enumerate(files):
        page = BookPage(
            book=book,
            number=start_number + index,
            file=upload,
            publish_at=start_at + timedelta(days=interval_days * index),
        )
        page.save()
        pages.append(page)
    return pages


# ---------- Kitobni PDF qilib yig'ish ----------

def _image_to_pdf_page(data: bytes) -> PdfReader:
    with Image.open(BytesIO(data)) as raw:
        img = ImageOps.exif_transpose(raw).convert("RGB")
    buffer = BytesIO()
    # Rasm kengligi A4 kengligiga teng bo'lsin — PDF sahifalari bir xil ko'rinadi
    img.save(buffer, "PDF", resolution=max(72.0, img.width / A4_WIDTH_INCH), quality=90)
    buffer.seek(0)
    return PdfReader(buffer)


def _signature(book: Book, pages: list[BookPage]) -> str:
    author = AuthorProfile.load()
    raw = "|".join([book.title, author.full_name] + [f"{p.pk}:{p.number}:{p.file.name}" for p in pages])
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def get_book_pdf(book: Book) -> Path | None:
    """Ochilgan sahifalardan bitta PDF yig'adi va keshlaydi.

    Yangi sahifa ochilsa yoki fayl almashsa, imzo o'zgaradi va PDF qayta yig'iladi.
    Hali ochilmagan sahifalar PDF ga hech qachon kirmaydi.
    """
    pages = list(open_pages(book))
    if not pages:
        return None

    cache_dir = Path(settings.PDF_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"book-{book.pk}-{_signature(book, pages)}.pdf"
    if target.exists():
        return target

    writer = PdfWriter()
    for page in pages:
        with page.file.open("rb") as fh:
            data = fh.read()
        reader = open_pdf(BytesIO(data)) if page.kind == BookPage.Kind.PDF else _image_to_pdf_page(data)
        for pdf_page in reader.pages:
            writer.add_page(pdf_page)

    author = AuthorProfile.load()
    writer.add_metadata({"/Title": book.title, "/Author": author.full_name or ""})

    tmp = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    with open(tmp, "wb") as out:
        writer.write(out)
    os.replace(tmp, target)

    for old in cache_dir.glob(f"book-{book.pk}-*.pdf"):
        if old != target:
            old.unlink(missing_ok=True)
    return target
