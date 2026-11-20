from rest_framework.generics import RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser

from .models import AuthorProfile
from .serializers import AuthorPanelSerializer, AuthorPublicSerializer


class AuthorPublicView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = AuthorPublicSerializer

    def get_object(self):
        return AuthorProfile.load()


class AuthorPanelView(RetrieveUpdateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AuthorPanelSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "patch", "options"]

    def get_object(self):
        return AuthorProfile.load()
