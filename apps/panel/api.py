from django.contrib.auth import authenticate, login, logout
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


def user_payload(user) -> dict:
    return {"username": user.get_username(), "name": user.get_full_name() or user.get_username()}


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        # DRF anonim foydalanuvchi uchun CSRF ni tekshirmaydi — login uchun o'zimiz tekshiramiz
        SessionAuthentication().enforce_csrf(request)
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, **serializer.validated_data)
        if user is None or not user.is_staff:
            return Response({"detail": "Login yoki parol noto'g'ri."}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response(user_payload(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(user_payload(request.user))
