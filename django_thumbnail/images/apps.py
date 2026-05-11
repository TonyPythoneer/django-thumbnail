from django.apps import AppConfig


class ImagesConfig(AppConfig):
    name = "images"

    def ready(self) -> None:
        from django.conf import settings
        from django_thumbnail.telemetry import setup_telemetry
        from opentelemetry.instrumentation.django import DjangoInstrumentor

        if str(settings.OTEL_SDK_DISABLED).lower() != "true":
            setup_telemetry(
                service_name=settings.OTEL_SERVICE_NAME,
                otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            )
            DjangoInstrumentor().instrument()
