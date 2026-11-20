from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from .models import Book, BookPage
from .selectors import published_books, with_page_counts
from .serializers import (
    BookDetailSerializer,
    BookListSerializer,
    BookPagePanelSerializer,
    BookPanelSerializer,
    BulkPageUploadSerializer,
)
from .services import create_pages_bulk

PANEL_PARSERS = [MultiPartParser, FormParser, JSONParser]


# ---------- Ochiq API ----------

class BookListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = BookListSerializer
    pagination_class = None

    def get_queryset(self):
        return with_page_counts(published_books())


class BookDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = BookDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return published_books().prefetch_related("pages")


# ---------- Admin panel ----------

class BookPanelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = BookPanelSerializer
    parser_classes = PANEL_PARSERS
    pagination_class = None

    def get_queryset(self):
        return with_page_counts(Book.objects.all())


class BookPagePanelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = BookPagePanelSerializer
    parser_classes = PANEL_PARSERS
    pagination_class = None

    def get_queryset(self):
        queryset = BookPage.objects.select_related("book").order_by("book_id", "number")
        book_id = self.request.query_params.get("book")
        if book_id is not None:
            if not book_id.isdigit():
                return queryset.none()
            queryset = queryset.filter(book_id=book_id)
        return queryset

    @action(detail=False, methods=["post"])
    def bulk(self, request):
        serializer = BulkPageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pages = create_pages_bulk(**serializer.validated_data)
        output = BookPagePanelSerializer(pages, many=True, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)
