from django.contrib.auth.models import User
from rest_framework.exceptions import NotAcceptable


def _check_user_already_exists(username, email):
    if (
        User.objects.filter(username=username).exists()
        or User.objects.filter(email=email).exists()
    ):
        raise NotAcceptable("User with this username or email already exists.")


def _check_email_already_exists(email):
    return _check_user_already_exists()


def _check_username_already_exists(email):
    return _check_user_already_exists()
