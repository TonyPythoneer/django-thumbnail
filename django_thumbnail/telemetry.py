from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


def _setup_provider() -> None:
    """Initialise global TracerProvider from Django settings. Idempotent."""
    # Default global provider is ProxyTracerProvider (no-op). Once we set a real
    # TracerProvider, subsequent calls (e.g. runserver reloader child process) skip reinit.
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return
    from django.conf import settings

    resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        SimpleSpanProcessor(
            OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
        )
    )
    trace.set_tracer_provider(tracer_provider)


def _instrument(*, django: bool) -> None:
    from django.conf import settings

    if settings.OTEL_SDK_DISABLED:
        return

    _setup_provider()
    from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    CeleryInstrumentor().instrument()
    BotocoreInstrumentor().instrument()
    if django:
        from opentelemetry.instrumentation.django import DjangoInstrumentor

        DjangoInstrumentor().instrument()


def setup_otel_for_django_web() -> None:
    """Call from AppConfig.ready()."""
    _instrument(django=True)


def setup_otel_for_celery_worker() -> None:
    """Call from worker_process_init signal."""
    _instrument(django=False)
