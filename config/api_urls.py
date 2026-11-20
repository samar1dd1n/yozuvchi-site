from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.author.api import AuthorPanelView, AuthorPublicView
from apps.books.api import BookDetailView, BookListView, BookPagePanelViewSet, BookPanelViewSet
from apps.books.views import book_pdf
from apps.panel.api import LoginView, LogoutView, MeView
from apps.posts.api import PostDetailView, PostListView, PostPanelViewSet

app_name = "api"

router = SimpleRouter()
router.register("panel/books", BookPanelViewSet, basename="panel-book")
router.register("panel/pages", BookPagePanelViewSet, basename="panel-page")
router.register("panel/posts", PostPanelViewSet, basename="panel-post")

urlpatterns = [
    # Ochiq (o'qish uchun)
    path("author/", AuthorPublicView.as_view(), name="author"),
    path("books/", BookListView.as_view(), name="book-list"),
    path("books/<str:slug>/", BookDetailView.as_view(), name="book-detail"),
    path("books/<str:slug>/pdf/", book_pdf, name="book-pdf"),
    path("posts/", PostListView.as_view(), name="post-list"),
    path("posts/<str:slug>/", PostDetailView.as_view(), name="post-detail"),
    # Kirish
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    # Admin panel (faqat is_staff)
    path("panel/author/", AuthorPanelView.as_view(), name="panel-author"),
    *router.urls,
]
