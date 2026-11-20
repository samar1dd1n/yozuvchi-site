from rest_framework import viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser

from .models import Post
from .selectors import published_posts
from .serializers import PostPanelSerializer, PostPublicSerializer


class PostListView(ListAPIView):
    """GET /api/posts/?kind=news|article|photo&page=2"""

    permission_classes = [AllowAny]
    serializer_class = PostPublicSerializer

    def get_queryset(self):
        queryset = published_posts()
        kind = self.request.query_params.get("kind")
        if kind in Post.Kind.values:
            queryset = queryset.filter(kind=kind)
        return queryset


class PostDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PostPublicSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return published_posts()


class PostPanelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = PostPanelSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = None
    queryset = Post.objects.all()
