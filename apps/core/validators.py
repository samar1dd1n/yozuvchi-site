from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.utils.deconstruct import deconstructible
from pypdf import PasswordType, PdfReader


@deconstructible
class MaxFileSizeValidator:
    def __init__(self, max_mb: int):
        self.max_mb = max_mb

    def __call__(self, file):
        if file and file.size > self.max_mb * 1024 * 1024:
            raise ValidationError(
                f"Fayl hajmi {self.max_mb} MB dan oshmasligi kerak.", code="file_too_large"
            )

    def __eq__(self, other):
        return isinstance(other, MaxFileSizeValidator) and other.max_mb == self.max_mb


IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
PAGE_EXTENSIONS = IMAGE_EXTENSIONS + ["pdf"]

IMAGE_VALIDATORS = [
    FileExtensionValidator(
        IMAGE_EXTENSIONS,
        message="Faqat JPG, PNG yoki WebP rasm yuklash mumkin.",
    ),
    MaxFileSizeValidator(15),
]

HEX_COLOR_VALIDATOR = RegexValidator(
    r"^#[0-9a-fA-F]{6}$", "Rang #RRGGBB ko'rinishida bo'lishi kerak, masalan #7a2e22."
)


def open_pdf(stream) -> PdfReader:
    """PDF ni o'qiydi; faqat ruxsatlar bilan qulflangan (parolsiz) PDF ni ham ochadi."""
    reader = PdfReader(stream)
    if reader.is_encrypted and reader.decrypt("") == PasswordType.NOT_DECRYPTED:
        raise ValidationError("Parol bilan himoyalangan PDF qabul qilinmaydi.")
    return reader


def validate_pdf_readable(file):
    name = (getattr(file, "name", "") or "").lower()
    if not name.endswith(".pdf"):
        return
    try:
        file.seek(0)
        reader = open_pdf(file)
        if len(reader.pages) == 0:
            raise ValidationError("PDF faylda birorta ham sahifa yo'q.")
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("PDF faylni o'qib bo'lmadi, fayl buzilgan bo'lishi mumkin.") from exc
    finally:
        file.seek(0)


PAGE_FILE_VALIDATORS = [
    FileExtensionValidator(
        PAGE_EXTENSIONS,
        message="Sahifa uchun JPG, PNG, WebP rasm yoki PDF yuklang.",
    ),
    MaxFileSizeValidator(50),
    validate_pdf_readable,
]
