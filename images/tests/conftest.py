import pytest
from django.contrib.auth.models import User
from django.test import Client

from .factories import UserFactory


@pytest.fixture
def user(db: None) -> User:
    return UserFactory()


@pytest.fixture
def other_user(db: None) -> User:
    return UserFactory()


@pytest.fixture
def auth_client(client: Client, user: User) -> tuple[Client, User]:
    client.force_login(user)
    return client, user
