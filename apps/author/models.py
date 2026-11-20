import re

from django.db import models

from apps.core.images import optimize_image
from apps.core.models import CleanupFilesMixin
from apps.core.uploads import UploadTo
from apps.core.validators import IMAGE_VALIDATORS

HANDLE_PREFIX = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me|instagram\.com)/", re.IGNORECASE
)


def normalize_handle(value: str) -> str:
    """'@ali', 'https://t.me/ali', 't.me/ali/' -> 'ali'."""
    value = HANDLE_PREFIX.sub("", (value or "").strip())
    return value.split("?")[0].strip("/").lstrip("@")


class AuthorProfile(CleanupFilesMixin, models.Model):
    """Saytda bitta muallif bor — jadvalda doim bitta qator (pk=1)."""

    full_name = models.CharField("Ism familiya", max_length=150, blank=True)
    tagline = models.CharField("Shior", max_length=255, blank=True)
    bio = models.TextField("Muallif haqida", blank=True)
    photo = models.ImageField(
        "Rasm", upload_to=UploadTo("author"), blank=True, validators=IMAGE_VALIDATORS
    )
    academic_degree = models.CharField("Ilmiy daraja", max_length=150, blank=True)
    science_field = models.CharField("Ilmiy soha", max_length=150, blank=True)
    telegram = models.CharField("Telegram", max_length=64, blank=True, help_text="Username, @ belgisiz")
    instagram = models.CharField("Instagram", max_length=64, blank=True, help_text="Username, @ belgisiz")
    email = models.EmailField("Email", blank=True)
    updated_at = models.DateTimeField("Yangilangan", auto_now=True)

    cleanup_file_fields = ("photo",)

    class Meta:
        verbose_name = "Muallif"
        verbose_name_plural = "Muallif"

    def __str__(self):
        return self.full_name or "Muallif"

    def save(self, *args, **kwargs):
        self.pk = 1
        self.telegram = normalize_handle(self.telegram)
        self.instagram = normalize_handle(self.instagram)
        if self.photo and not self.photo._committed:
            self.photo = optimize_image(self.photo, max_side=1600).content
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Muallif yozuvi o'chirilmaydi, faqat tahrirlanadi
        return 0, {}

    @classmethod
    def load(cls) -> "AuthorProfile":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def telegram_url(self) -> str:
        return f"https://t.me/{self.telegram}" if self.telegram else ""

    @property
    def instagram_url(self) -> str:
        return f"https://instagram.com/{self.instagram}" if self.instagram else ""

    @property
    def has_contacts(self) -> bool:
        return bool(self.telegram or self.instagram or self.email)
