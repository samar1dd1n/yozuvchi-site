import re

from django.utils.text import slugify

APOSTROPHES = re.compile(r"[ʻʼ'’‘`]")


def unique_slug(instance, value: str, *, fallback: str, field: str = "slug", max_length: int = 200) -> str:
    """Sarlavhadan noyob slug yasaydi: "Oʻzbek tili" -> "ozbek-tili", band bo'lsa "ozbek-tili-2"."""
    base = slugify(APOSTROPHES.sub("", value or ""), allow_unicode=True)[:max_length].strip("-") or fallback
    manager = type(instance)._default_manager
    queryset = manager.exclude(pk=instance.pk) if instance.pk else manager.all()

    slug, counter = base, 2
    while queryset.filter(**{field: slug}).exists():
        suffix = f"-{counter}"
        slug = f"{base[: max_length - len(suffix)]}{suffix}"
        counter += 1
    return slug
