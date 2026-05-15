import sys

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "django_thumbnail"
    label = "core"

    def ready(self) -> None:
        if not _is_web_server_process():
            return
        from django_thumbnail.telemetry import setup_otel_for_django_web

        setup_otel_for_django_web()


def _is_web_server_process() -> bool:
    # Avoid initialising OTel in the Celery worker parent (would inherit the
    # gRPC channel across fork) or in management commands (e.g. migrate, shell).
    # The worker child sets up its own provider via worker_process_init.
    argv0 = sys.argv[0] if sys.argv else ""
    return ("gunicorn" in argv0 or "uvicorn" in argv0) or "runserver" in sys.argv
