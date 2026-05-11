from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

USERS = [
    {"email": "test1@example.com", "password": "test1"},
    {"email": "test2@example.com", "password": "test2"},
]


class Command(BaseCommand):
    help = "Create permanent test accounts"

    def handle(self, *args, **options):
        for u in USERS:
            username = u["email"]
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": username},
            )
            user.set_password(u["password"])
            user.save()
            status = "created" if created else "updated"
            self.stdout.write(f"{status}: {username}")
