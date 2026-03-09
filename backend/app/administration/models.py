import random
import string
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.conf import settings


class UserManager(BaseUserManager):
    def create_user(self, phone_number, name='', password=None, **extra_fields):
        if not phone_number:
            raise ValueError('Номер телефона обязателен')
        user = self.model(phone_number=phone_number, name=name, **extra_fields)
        user.set_unusable_password()
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, name='', password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        user = self.model(phone_number=phone_number, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=20, unique=True, verbose_name='Номер телефона')
    name = models.CharField(max_length=150, blank=True, verbose_name='Имя')
    email = models.EmailField(blank=True, verbose_name='Электронная почта')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_staff = models.BooleanField(default=False, verbose_name='Персонал')
    date_joined = models.DateTimeField(default=timezone.now, verbose_name='Дата регистрации')

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.phone_number} ({self.name or "без имени"})'


class DeliveryAddress(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name='Пользователь'
    )
    address = models.TextField(verbose_name='Адрес')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        verbose_name = 'Адрес доставки'
        verbose_name_plural = 'Адреса доставки'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.phone_number} — {self.address}'


class AuthCode(models.Model):
    phone_number = models.CharField(max_length=20, verbose_name='Номер телефона')
    code = models.CharField(max_length=6, verbose_name='Код')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    is_used = models.BooleanField(default=False, verbose_name='Использован')

    class Meta:
        verbose_name = 'Код авторизации'
        verbose_name_plural = 'Коды авторизации'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.phone_number} — {self.code}'

    @classmethod
    def generate_code(cls):
        return ''.join(random.choices(string.digits, k=6))

    def is_expired(self):
        from datetime import timedelta
        expiry = self.created_at + timedelta(minutes=settings.AUTH_CODE_EXPIRY_MINUTES)
        return timezone.now() > expiry
