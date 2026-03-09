from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RequestAuthCodeView,
    VerifyAuthCodeView,
    UserCreateView,
    UserDetailView,
)

urlpatterns = [
    path('request-code/', RequestAuthCodeView.as_view(), name='auth-request-code'),
    path('verify-code/', VerifyAuthCodeView.as_view(), name='auth-verify-code'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('users/', UserCreateView.as_view(), name='user-create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
]
