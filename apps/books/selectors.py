from dataclasses import dataclass

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from .models import Book, BookPage


def published_books() -> QuerySet[Book]:
    return Book.objects.filter(is_published=True)


def visible_books(user) -> QuerySet[Book]:
    """Admin yashirin kitoblarni ham ko'radi (oldindan ko'rish uchun)."""
    return Book.objects.all() if user.is_staff else published_books()


def with_page_counts(queryset: QuerySet[Book]) -> QuerySet[Book]:
    now = timezone.now()
    return queryset.annotate(
        pages_count=Count("pages", distinct=True),
        open_pages_count=Count("pages", filter=Q(pages__publish_at__lte=now), distinct=True),
    )


def open_pages(book: Book) -> QuerySet[BookPage]:
    return book.pages.filter(publish_at__lte=timezone.now()).order_by("number")


@dataclass
class PageOverview:
    opened: list[BookPage]
    locked_preview: list[BookPage]
    locked_rest: int
    total: int
    next_page: BookPage | None

    @property
    def open_count(self) -> int:
        return len(self.opened)


def page_overview(book: Book, locked_preview: int = 6) -> PageOverview:
    """Ochilgan sahifalar + navbatdagi bir nechta qulflangan sahifa."""
    now = timezone.now()
    pages = list(book.pages.order_by("number"))
    opened = [p for p in pages if p.publish_at <= now]
    locked = [p for p in pages if p.publish_at > now]
    next_page = min(locked, key=lambda p: p.publish_at) if locked else None
    return PageOverview(
        opened=opened,
        locked_preview=locked[:locked_preview],
        locked_rest=max(0, len(locked) - locked_preview),
        total=len(pages),
        next_page=next_page,
    )
