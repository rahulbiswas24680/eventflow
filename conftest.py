import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from pytest_factoryboy import register
from user_profiles.tests.factories import UserFactory
from rest_framework.test import APIClient

User = get_user_model()
register(UserFactory)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_group(db):
    return Group.objects.create(name="User Group")


@pytest.fixture
def staff_group(db):
    return Group.objects.create(name="Staff Group")


@pytest.fixture
def registered_user(db, user_group):
    user = User.objects.create_user(
        username="testuser",
        first_name="Test",
        last_name="User",
        email="testuser@example.com",
        password="testpassword",
    )
    user.groups.add(user_group)
    return user


@pytest.fixture
def registration_payload():
    return {
        "password": "password",
        "is_superuser": False,
        "is_staff": False,
        "username": "pranab",
        "first_name": "Pranab",
        "last_name": "Saha",
        "email": "pranabsaha@gmail.com",
    }


@pytest.fixture
def login_payload(registered_user):
    return {
        "email": registered_user.email,
        "password": "testpassword",
    }


@pytest.fixture(autouse=True)
def configure_test_environment(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    settings.SESSION_ENGINE = "django.contrib.sessions.backends.db"
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.CELERY_BROKER_URL = "memory://"
    settings.CELERY_RESULT_BACKEND = "cache+memory://"
