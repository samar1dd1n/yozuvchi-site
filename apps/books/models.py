from django.db import models
from django.utils import timezone

from apps.core.images import edge_color, optimize_image, readable_ink
from apps.core.models import CleanupFilesMixin, TimeStampedModel
from apps.core.uploads import UploadTo
from apps.core.utils import unique_slug
from apps.core.validators import HEX_COLOR_VALIDATOR, IMAGE_VALIDATORS, PAGE_FILE_VALIDATORS

DEFAULT_SPINE_COLOR = "#7a2e22"
DEFAULT_COVER_RATIO = 1.4  # 5:7


class Book(CleanupFilesMixin, TimeStampedModel):
    title = models.CharField("Kitob nomi", max_length=255)
    slug = models.SlugField("Havola nomi", max_length=255, unique=True, allow_unicode=True, blank=True)
    annotation = models.TextField("Annotatsiya", blank=True)
    cover = models.ImageField("Muqova rasmi", upload_to=UploadTo("covers"), validators=IMAGE_VALIDATORS)
    back_cover = models.ImageField(
        "Orqa muqova", upload_to=UploadTo("covers"), blank=True, validators=IMAGE_VALIDATORS
    )
    cover_width = models.PositiveIntegerField(default=0, editable=False)
    cover_height = models.PositiveIntegerField(default=0, editable=False)
    spine_color = models.CharField(
        "Qirra rangi",
        max_length=7,
        blank=True,
        validators=[HEX_COLOR_VALIDATOR],
        help_text="Bo'sh qoldirilsa, muqovaning chap chetidan avtomatik olinadi",
    )
    auto_spine_color = models.CharField(max_length=7, blank=True, editable=False)
    is_published = models.BooleanField("Saytda ko'rinsin", default=True)
    order = models.PositiveIntegerField("Tartib", default=0)

    cleanup_file_fields = ("cover", "back_cover")

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = "Kitob"
        verbose_name_plural = "Kitoblar"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title, fallback="kitob")
        if self.cover and not self.cover._committed:
            processed = optimize_image(self.cover, max_side=2000)
            self.cover = processed.content
            self.cover_width, self.cover_height = processed.width, processed.height
            self.auto_spine_color = edge_color(processed.image)
        if self.back_cover and not self.back_cover._committed:
            self.back_cover = optimize_image(self.back_cover, max_side=2000).content
        super().save(*args, **kwargs)

    @property
    def effective_spine_color(self) -> str:
        return self.spine_color or self.auto_spine_color or DEFAULT_SPINE_COLOR

    @property
    def spine_text_color(self) -> str:
        return readable_ink(self.effective_spine_color)

    @property
    def cover_ratio(self) -> float:
        if self.cover_width and self.cover_height:
            return self.cover_height / self.cover_width
        return DEFAULT_COVER_RATIO


class BookPage(CleanupFilesMixin, TimeStampedModel):
    """Kitobning bitta yuklangan sahifasi (rasm yoki PDF).

    publish_at kelmaguncha sahifa saytda qulf bilan ko'rinadi, fayli berilmaydi.
    """

    class Kind(models.TextChoices):
        IMAGE = "image", "Rasm"
        PDF = "pdf", "PDF"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="pages", verbose_name="Kitob")
    number = models.PositiveIntegerField("Sahifa raqami")
    file = models.FileField("Fayl", upload_to=UploadTo("pages"), validators=PAGE_FILE_VALIDATORS)
    kind = models.CharField("Turi", max_length=10, choices=Kind.choices, editable=False, default=Kind.IMAGE)
    pdf_page_count = models.PositiveSmallIntegerField("PDF betlar soni", default=1, editable=False)
    thumbnail = models.ImageField(upload_to=UploadTo("thumbs"), blank=True, editable=False)
    publish_at = models.DateTimeField("Ochilish vaqti", default=timezone.now, db_index=True)

    cleanup_file_fields = ("file", "thumbnail")

    class Meta:
        ordering = ["number"]
        verbose_name = "Sahifa"
        verbose_name_plural = "Sahifalar"
        constraints = [
            models.UniqueConstraint(fields=["book", "number"], name="unique_page_number_per_book"),
        ]

    def __str__(self):
        return f"{self.book} — {self.number}-sahifa"

    def save(self, *args, **kwargs):
        if self.file and not self.file._committed:
            from .services import prepare_page_upload

            prepare_page_upload(self)
        super().save(*args, **kwargs)

    @property
    def is_open(self) -> bool:
        return self.publish_at <= timezone.now()
