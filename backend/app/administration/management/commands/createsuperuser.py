"""
Custom createsuperuser command.

Asks for email + password only (phone_number is auto-generated as a placeholder,
since the Django admin login uses email via EmailAuthBackend).
"""

import uuid
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a superuser with email and password (for Django admin login)'

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Email address')
        parser.add_argument('--password', help='Password (use only in scripts/CI)')
        parser.add_argument('--name', default='', help='Display name (optional)')

    def handle(self, *args, **options):
        email = options.get('email')
        password = options.get('password')
        name = options.get('name', '')

        # --- email ---
        if not email:
            while True:
                email = input('Email: ').strip()
                try:
                    validate_email(email)
                except ValidationError:
                    self.stderr.write('Введите корректный email.')
                    continue
                if User.objects.filter(email=email).exists():
                    self.stderr.write(f'Пользователь с email {email} уже существует.')
                    continue
                break
        else:
            try:
                validate_email(email)
            except ValidationError:
                self.stderr.write(self.style.ERROR('Некорректный email.'))
                return

        # --- password ---
        if not password:
            import getpass
            while True:
                password = getpass.getpass('Password: ')
                password2 = getpass.getpass('Password (again): ')
                if password != password2:
                    self.stderr.write('Пароли не совпадают.')
                    continue
                if len(password) < 8:
                    self.stderr.write('Пароль слишком короткий (минимум 8 символов).')
                    continue
                break

        # Generate a unique placeholder phone_number (field required by model, not used for admin login)
        phone_number = f'su_{uuid.uuid4().hex[:14]}'

        user = User.objects.create_superuser(
            phone_number=phone_number,
            name=name,
            password=password,
            email=email,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Суперпользователь создан. Войдите в /admin/ с email: {user.email}'
            )
        )
