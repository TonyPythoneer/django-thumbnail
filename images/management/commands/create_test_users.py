from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create permanent test accounts defined in settings.TEST_USERS"

    def handle(self, *args: object, **options: object) -> None:
        users: list[tuple[str, str]] = list(settings.TEST_USERS)
        if not users:
            self.stdout.write(self.style.WARNING("settings.TEST_USERS empty, skipping"))
            return
        if self._all_present(users):
            self.stdout.write("test accounts already exist, skipping")
            return
        self._create(users)
        self.stdout.write("test accounts created")

    def _all_present(self, users: list[tuple[str, str]]) -> bool:
        emails = [email for email, _ in users]
        return User.objects.filter(username__in=emails).count() == len(users)

    def _create(self, users: list[tuple[str, str]]) -> None:
        for username, password in users:
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(
                    username=username,
                    email=username,
                    password=password,
                )
