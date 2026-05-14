import os
from celery import Celery
from celery.signals import worker_process_init

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_thumbnail.settings.local")

app = Celery("django_thumbnail")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@worker_process_init.connect
def init_worker_telemetry(**kwargs: object) -> None:
    from django_thumbnail.telemetry import setup_otel_for_celery_worker

    setup_otel_for_celery_worker()
