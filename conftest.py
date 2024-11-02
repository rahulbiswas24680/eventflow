import pytest
from django.contrib.auth.models import Group, User
from pytest_factoryboy import register
from tests.factories import UserFactory
from rest_framework.test import APIClient


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
    return User.objects.create(
        username="testuser",
        first_name="Test",
        last_name="User",
        email="testuser@example.com",
        password="testpassword",
    )


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
