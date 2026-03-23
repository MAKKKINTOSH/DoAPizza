from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import AuthCode, User


class RequestAuthCodeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/request-code/'

    def test_returns_200_and_detail(self):
        response = self.client.post(self.url, {'phone_number': '+79001234567'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('detail', response.data)

    def test_creates_auth_code_in_db(self):
        self.client.post(self.url, {'phone_number': '+79001234567'}, format='json')
        self.assertTrue(AuthCode.objects.filter(phone_number='+79001234567', is_used=False).exists())

    def test_invalidates_previous_codes(self):
        AuthCode.objects.create(phone_number='+79001234567', code='111111', is_used=False)
        self.client.post(self.url, {'phone_number': '+79001234567'}, format='json')
        old_code = AuthCode.objects.get(code='111111')
        self.assertTrue(old_code.is_used)

    def test_missing_phone_returns_400(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)


class VerifyAuthCodeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/verify-code/'
        self.phone = '+79001234567'

    def test_valid_code_returns_jwt_and_user(self):
        AuthCode.objects.create(phone_number=self.phone, code='482910', is_used=False)
        response = self.client.post(self.url, {'phone_number': self.phone, 'code': '482910'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['phone_number'], self.phone)

    def test_valid_code_creates_user_if_not_exists(self):
        AuthCode.objects.create(phone_number=self.phone, code='482910', is_used=False)
        self.client.post(self.url, {'phone_number': self.phone, 'code': '482910'}, format='json')
        self.assertTrue(User.objects.filter(phone_number=self.phone).exists())

    def test_valid_code_marks_as_used(self):
        auth_code = AuthCode.objects.create(phone_number=self.phone, code='482910', is_used=False)
        self.client.post(self.url, {'phone_number': self.phone, 'code': '482910'}, format='json')
        auth_code.refresh_from_db()
        self.assertTrue(auth_code.is_used)

    def test_invalid_code_returns_400(self):
        AuthCode.objects.create(phone_number=self.phone, code='111111', is_used=False)
        response = self.client.post(self.url, {'phone_number': self.phone, 'code': '999999'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)

    def test_already_used_code_returns_400(self):
        AuthCode.objects.create(phone_number=self.phone, code='111111', is_used=True)
        response = self.client.post(self.url, {'phone_number': self.phone, 'code': '111111'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_expired_code_returns_400(self):
        code = AuthCode.objects.create(phone_number=self.phone, code='111111', is_used=False)
        AuthCode.objects.filter(pk=code.pk).update(created_at=timezone.now() - timedelta(minutes=15))
        response = self.client.post(self.url, {'phone_number': self.phone, 'code': '111111'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)

    def test_magic_code_123456_returns_jwt(self):
        response = self.client.post(self.url, {'phone_number': self.phone, 'code': '123456'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)


class UserCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/users/'

    def test_create_user_returns_201(self):
        response = self.client.post(self.url, {'phone_number': '+79001234567'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['phone_number'], '+79001234567')

    def test_create_user_with_name_and_email(self):
        response = self.client.post(
            self.url,
            {'phone_number': '+79001234567', 'name': 'Иван', 'email': 'ivan@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'Иван')
        self.assertEqual(response.data['email'], 'ivan@example.com')

    def test_duplicate_phone_returns_400(self):
        User.objects.create(phone_number='+79001234567')
        response = self.client.post(self.url, {'phone_number': '+79001234567'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_missing_phone_returns_400(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)


class UserDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(phone_number='+79001234567', name='Иван')

    def test_returns_user_data(self):
        response = self.client.get(f'/api/auth/users/{self.user.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['phone_number'], '+79001234567')
        self.assertIn('addresses', response.data)

    def test_nonexistent_user_returns_404(self):
        response = self.client.get('/api/auth/users/99999/')
        self.assertEqual(response.status_code, 404)
