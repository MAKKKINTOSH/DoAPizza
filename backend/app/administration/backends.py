from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailAuthBackend(ModelBackend):
    """Authenticate using email + password (for Django admin login)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(email=username, is_staff=True).first()
            if user is None:
                user = User.objects.filter(email=username).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
