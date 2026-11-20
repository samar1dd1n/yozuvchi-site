from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator

from apps.core.images import optimize_image
from apps.core.models import CleanupFilesMixin, TimeStampedModel
from apps.core.uploads import UploadTo
from apps.core.utils import unique_slug
from apps.core.validators import IMAGE_VALIDATORS


class Post(CleanupFilesMixin, TimeStampedModel):
    class Kind(models.TextChoices):
        NEWS = "news", "Yangilik"
        ARTICLE = "article", "Maqola"
        PHOTO = "photo", "Rasm"

    title = models.CharField("Sarlavha", max_length=255)
    slug = models.SlugField("Havola nomi", max_length=255, unique=True, allow_unicode=True, blank=True)
    kind = models.CharField("Turi", max_length=20, choices=Kind.choices, default=Kind.NEWS)
    excerpt = models.CharField("Qisqa tavsif", max_length=300, blank=True)
    body = models.TextField("Matn", blank=True)
    image = models.ImageField(
        "Rasm", upload_to=UploadTo("posts"), blank=True, validators=IMAGE_VALIDATORS
    )
    is_published = models.BooleanField("Saytda ko'rinsin", default=True)
    published_at = models.DateTimeField("E'lon vaqti", default=timezone.now, db_index=True)

    cleanup_file_fields = ("image",)

    class Meta:
        ordering = ["-published_at", "-id"]
        verbose_name = "Fikr"
        verbose_name_plural = "Fikrlar"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title, fallback="post")
        if self.image and not self.image._committed:
            self.image = optimize_image(self.image, max_side=1800).content
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("web:post-detail", args=[self.slug])

    @property
    def summary(self) -> str:
        return self.excerpt or Truncator(self.body).chars(220)

    @property
    def is_live(self) -> bool:
        return self.is_published and self.published_at <= timezone.now()
