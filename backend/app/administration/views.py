from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    RequestAuthCodeSerializer,
    VerifyAuthCodeSerializer,
)


MOCK_CODE = '123456'

class RequestAuthCodeView(APIView):
    """
    POST /api/auth/request-code/
    Мок-режим: код не отправляется, для входа используйте 123456.
    """

    def post(self, request):
        serializer = RequestAuthCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            {'detail': 'Код отправлен в Telegram. Введите его для входа.'},
            status=status.HTTP_200_OK,
        )


class VerifyAuthCodeView(APIView):
    """
    POST /api/auth/verify-code/
    Мок-режим: код 123456 принимается для любого номера телефона.
    """

    def post(self, request):
        serializer = VerifyAuthCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        if code != MOCK_CODE:
            return Response(
                {'detail': 'Неверный или уже использованный код.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, _ = User.objects.get_or_create(phone_number=phone_number)

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
