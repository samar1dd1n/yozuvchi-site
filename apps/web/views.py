from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from apps.books.selectors import page_overview, visible_books
from apps.posts.models import Post
from apps.posts.selectors import published_posts, visible_posts

POSTS_PER_PAGE = 9


@require_GET
def home(request):
    return render(request, "web/home.html")


@require_GET
def book(request, slug=None):
    books = visible_books(request.user)
    current = get_object_or_404(books, slug=slug) if slug else books.first()
    context = {"book": current}

    if current is not None:
        overview = page_overview(current)
        ratio = min(max(current.cover_ratio, 1.0), 1.8)
        thickness = 24 + min(overview.total, 120) * 0.25  # sahifa ko'paygan sari kitob qalinlashadi
        context.update(
            overview=overview,
            pdf_url=reverse("api:book-pdf", args=[current.slug]) if overview.open_count else None,
            # Raqamlar locale'siz yoziladi, aks holda CSS buziladi (1,4 emas 1.4)
            stage_style=(
                f"--ratio:{ratio:.4f};--d:{thickness:.1f}px;"
                f"--spine:{current.effective_spine_color};--spine-ink:{current.spine_text_color}"
            ),
            other_books=books.exclude(pk=current.pk),
        )
    return render(request, "web/book.html", context)


@require_GET
def posts(request):
    kind = request.GET.get("tur", "")
    if kind not in Post.Kind.values:
        kind = ""

    queryset = published_posts()
    if kind:
        queryset = queryset.filter(kind=kind)

    page_obj = Paginator(queryset, POSTS_PER_PAGE).get_page(request.GET.get("sahifa"))
    items = list(page_obj.object_list)
    featured = items.pop(0) if page_obj.number == 1 and items else None

    return render(
        request,
        "web/posts.html",
        {
            "kind": kind,
            "filters": [("", "Barchasi"), *Post.Kind.choices],
            "page_obj": page_obj,
            "featured": featured,
            "items": items,
        },
    )


@require_GET
def post_detail(request, slug):
    post = get_object_or_404(visible_posts(request.user), slug=slug)
    recent = published_posts().exclude(pk=post.pk)[:3]
    return render(request, "web/post_detail.html", {"post": post, "recent": recent})


@require_GET
def robots(request):
    lines = ["User-agent: *", "Disallow: /panel/", "Disallow: /api/", "Disallow: /django-admin/"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
