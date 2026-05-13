import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_thumbnail.settings.local")

app = Celery("django_thumbnail")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
