import pytest
from django.contrib.auth.models import User
from django.test import Client

from .factories import make_user


@pytest.fixture
def user(db: None) -> User:
    return make_user()


@pytest.fixture
def other_user(db: None) -> User:
    return make_user()


@pytest.fixture
def auth_client(client: Client, user: User) -> tuple[Client, User]:
    client.force_login(user)
    return client, user
