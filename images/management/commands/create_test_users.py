from typing import NamedTuple

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class TestUser(NamedTuple):
    email: str
    password: str


USERS = [
    TestUser("test1@example.com", "test1"),
    TestUser("test2@example.com", "test2"),
]


class Command(BaseCommand):
    help = "Create permanent test accounts"

    def handle(self, *args, **options):
        if self.check_created_test_accounts():
            self.stdout.write("test accounts already exist, skipping")
            return
        self.create_test_accounts()
        self.stdout.write("test accounts created")

    def check_created_test_accounts(self) -> bool:
        emails = [email for email, _ in USERS]
        return User.objects.filter(username__in=emails).count() == len(USERS)

    def create_test_accounts(self) -> None:
        for username, password in USERS:
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(
                    username=username,
                    email=username,
                    password=password,
                )
