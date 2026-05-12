from .base import *  # noqa: F401, F403

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "django_thumbnail_test",
        "USER": "django_thumbnail",
        "PASSWORD": "django_thumbnail",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use in-memory storage — no real MinIO needed in tests
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Suppress OTel in tests
OTEL_SDK_DISABLED = "true"
