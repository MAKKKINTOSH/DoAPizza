from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

from .models import User, AuthCode
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    RequestAuthCodeSerializer,
    VerifyAuthCodeSerializer,
)


class RequestAuthCodeView(APIView):
    """
    POST /api/auth/request-code/
    Запрашивает код авторизации для указанного номера телефона.
    В реальном сценарии код отправляется через Telegram-бота.
    """

    def post(self, request):
        serializer = RequestAuthCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']

        # Инвалидируем предыдущие неиспользованные коды
        AuthCode.objects.filter(phone_number=phone_number, is_used=False).update(is_used=True)

        code = AuthCode.generate_code()
        AuthCode.objects.create(phone_number=phone_number, code=code)

        # TODO: отправить code через Telegram-бота на указанный номер телефона
        # telegram_bot.send_code(phone_number, code)

        return Response(
            {'detail': 'Код отправлен в Telegram. Введите его для входа.'},
            status=status.HTTP_200_OK,
        )


class VerifyAuthCodeView(APIView):
    """
    POST /api/auth/verify-code/
    Проверяет код авторизации и возвращает JWT-токены.
    """

    def post(self, request):
        serializer = VerifyAuthCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        try:
            auth_code = AuthCode.objects.filter(
                phone_number=phone_number,
                code=code,
                is_used=False,
            ).latest('created_at')
        except AuthCode.DoesNotExist:
            return Response(
                {'detail': 'Неверный или уже использованный код.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if auth_code.is_expired():
            return Response(
                {'detail': 'Срок действия кода истёк.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        auth_code.is_used = True
        auth_code.save()

        user, created = User.objects.get_or_create(phone_number=phone_number)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


class UserCreateView(CreateAPIView):
    """
    POST /api/auth/users/
    Создание нового пользователя.
    """
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer


class UserDetailView(RetrieveAPIView):
    """
    GET /api/auth/users/{id}/
    Получение данных пользователя по id, включая прошлые адреса.
    """
    queryset = User.objects.prefetch_related('addresses').all()
    serializer_class = UserSerializer
