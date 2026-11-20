from django.db.models import QuerySet
from django.utils import timezone

from .models import Post


def published_posts() -> QuerySet[Post]:
    """Saytda ko'rinadigan postlar: yoqilgan va e'lon vaqti kelgan."""
    return Post.objects.filter(is_published=True, published_at__lte=timezone.now())


def visible_posts(user) -> QuerySet[Post]:
    return Post.objects.all() if user.is_staff else published_posts()
