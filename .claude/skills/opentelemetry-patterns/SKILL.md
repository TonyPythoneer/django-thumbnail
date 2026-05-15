---
name: opentelemetry-patterns
description: OpenTelemetry patterns for django-thumbnail — batch span attributes via set_attributes(dict), web vs Celery worker telemetry separation, instrumentor wiring, and OTLP/Jaeger exporter config. Use when modifying telemetry.py, adding spans to tasks or views, or debugging trace coverage.
---

# OpenTelemetry Patterns

This project exports OTLP/gRPC spans to a local Jaeger collector. All setup lives in `django_thumbnail/telemetry.py`. Web and Celery worker processes wire instrumentors at **different lifecycle points** — getting this wrong silently drops every span.

## When to Use

Apply this skill when:
- Modifying `django_thumbnail/telemetry.py`, `django_thumbnail/apps.py`, or `django_thumbnail/celery.py`
- Adding `span.set_attribute(s)` calls in `images/tasks.py`, `images/views.py`, or any new code path
- Adding a new OTel instrumentor package (must appear in `pyproject.toml` AND be wired in `_instrument()`)
- Debugging missing spans in Jaeger (`SMOKE_JAEGER_BASE_URL`, default `http://localhost:16686`)
- Touching the test settings flag that disables OTel

## Core Patterns

### Batch span attributes — `span.set_attributes(dict)`

**Hard rule**: never call `span.set_attribute()` multiple times in a row. Always accumulate into a `dict` and call `span.set_attributes(dict)` once.

Why:
- Each `set_attribute()` call is a separate SDK touch; batching is cheaper and more readable.
- A single dict in `finally` guarantees attributes are written exactly once even when the happy/error branches diverge.

Canonical pattern from `images/tasks.py::generate_thumbnail`:

```python
span = trace.get_current_span()
span_attributes = {
    "task_id": celery_id,
    "image_task_id": image_task_id,
    "image_id": str(task.image.id),
    "user_id": str(task.image.user_id),
    "image_name": task.image.original_filename,
}
try:
    ...
    span_attributes["status"] = Outcome.DONE
except InvalidImageError:
    ...
    span_attributes["status"] = Outcome.INVALID
except Exception as exc:
    span_attributes["status"] = Outcome.FAIL  # or RETRY
    span.record_exception(exc)
    raise self.retry(...)
finally:
    span.set_attributes(span_attributes)
```

Note: `span.record_exception(exc)` is the correct way to attach exception detail — do not jam a stringified traceback into the attributes dict.

### Web vs Celery worker telemetry separation

The split exists because **Celery prefork workers don't inherit the gRPC exporter thread/channel across `fork()`** — if you instrument in the parent, no span ever reaches Jaeger from the child. (See commit `af308f6`: "refactor(otel): split telemetry setup for web vs Celery worker".)

Two entry points in `django_thumbnail/telemetry.py`:

| Entry point | Caller | When it runs | `django` instrumentor |
|---|---|---|---|
| `setup_otel_for_django_web()` | `django_thumbnail/apps.py::CoreConfig.ready()` | Web server startup only | Yes |
| `setup_otel_for_celery_worker()` | `django_thumbnail/celery.py::init_worker_telemetry` (handler of `worker_process_init`) | Each worker child after fork | No |

Both go through the private `_instrument(django: bool)` which:
1. Returns early when `settings.OTEL_SDK_DISABLED` is true.
2. Calls `_setup_provider()` (idempotent — bails if the current `TracerProvider` is already a real `TracerProvider`, not the no-op `ProxyTracerProvider`).
3. Wires `CeleryInstrumentor` and `BotocoreInstrumentor` in both processes.
4. Wires `DjangoInstrumentor` only when `django=True`.

**Process-detection guard** in `django_thumbnail/apps.py::_is_web_server_process()` — `ready()` runs for *every* Django entry point (migrations, shell, the Celery parent), so OTel setup is gated to argv containing `gunicorn`, `uvicorn`, or `runserver`. Without this, the worker parent would set up OTel before fork and break export.

### Instrumentor wiring locations

Concrete file:function map — touch these and nothing else:

- `django_thumbnail/telemetry.py::_instrument()` — the only place that calls `.instrument()` on any instrumentor.
- `django_thumbnail/apps.py::CoreConfig.ready()` — invokes the web path, guarded by `_is_web_server_process()`.
- `django_thumbnail/celery.py::init_worker_telemetry` — `@worker_process_init.connect`, invokes the worker path.

Active instrumentors (must match `pyproject.toml`):
- `opentelemetry-instrumentation-django` → `DjangoInstrumentor` (web only)
- `opentelemetry-instrumentation-celery` → `CeleryInstrumentor` (both)
- `opentelemetry-instrumentation-botocore` → `BotocoreInstrumentor` (both — covers boto3/MinIO via `internal_s3` and `public_s3`)

To add a new instrumentor (e.g. psycopg, redis), add the package to `pyproject.toml` *and* import/call it inside `_instrument()` — adding the package alone is a no-op.

### OTLP / Jaeger exporter (env-driven)

Exporter is gRPC OTLP, configured by env-driven Django settings (`django_thumbnail/settings/base.py`):

```python
OTEL_SDK_DISABLED = os.environ.get("OTEL_SDK_DISABLED", "false").lower() == "true"
OTEL_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "django-thumbnail")
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
```

**Important — per-process service name**: `docker-compose.yml` overrides `OTEL_SERVICE_NAME` separately for each service so the web app and the Celery worker show up as distinct services in Jaeger:

- web container: `OTEL_SERVICE_NAME=django-thumbnail-app`
- worker container: `OTEL_SERVICE_NAME=django-thumbnail-worker`

`images/tests/test_smoke.py` relies on this split when querying Jaeger by service. When adding new processes (e.g., beat, flower), give them their own distinct service name — never share the base default across processes, or traces will collapse into a single service in Jaeger.

Wired in `telemetry.py::_setup_provider()`:

```python
resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(
    SimpleSpanProcessor(
        OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
    )
)
```

Rules:
- **Never hardcode** an endpoint, service name, or `insecure=` value — read from `settings.*`, which reads from env.
- `SimpleSpanProcessor` is deliberate. `BatchSpanProcessor` was avoided because its background flush thread doesn't survive fork (this is what commit `af308f6` fixed). Don't swap it back without re-checking worker behaviour.
- Jaeger UI lives at `SMOKE_JAEGER_BASE_URL` (default `http://localhost:16686`); the collector ingest is `OTEL_EXPORTER_OTLP_ENDPOINT` (default `localhost:4317`). Different ports.

### Test mode (OTel disabled)

`django_thumbnail/settings/test.py` sets:

```python
OTEL_SDK_DISABLED = True
```

Effect: `_instrument()` returns immediately, no `TracerProvider` is installed, so `trace.get_current_span()` returns the no-op `INVALID_SPAN`. `span.set_attributes({...})` and `span.record_exception(...)` are safe to leave in production code paths — they are no-ops in tests.

Do not branch on `settings.OTEL_SDK_DISABLED` in business code. The no-op span handles it.

## Anti-Patterns

- Repeated `span.set_attribute("k1", v1); span.set_attribute("k2", v2)` — batch into one `set_attributes({...})`.
- Calling `*.instrument()` outside `_instrument()` — bypasses the disabled flag and the fork-safety design.
- Wiring `DjangoInstrumentor` from the Celery worker path — adds noise and risks middleware double-wrap.
- Adding an instrumentor package to `pyproject.toml` without calling `.instrument()` in `_instrument()` — silent no-op.
- Swapping `SimpleSpanProcessor` for `BatchSpanProcessor` without verifying Celery worker fork behaviour.
- Hardcoding the OTLP endpoint or service name in code instead of reading the Django setting.
- Removing `_is_web_server_process()` in `apps.py` — Celery parent's `AppConfig.ready()` would then instrument before fork.
- Branching application logic on `OTEL_SDK_DISABLED` — let the no-op tracer absorb it.
- Wrapping span access in `if span.is_recording()` for simple attribute writes — `set_attributes` on a no-op span is already cheap.

## Integration with Other Skills

- **celery-patterns** — the `finally: span.set_attributes(span_attributes)` block is part of the canonical `generate_thumbnail` shape; retry/permanent-failure branches each set `status` before the `finally` runs.
- **storage-s3** — `BotocoreInstrumentor` automatically traces calls through `images/storage.py` (`internal_s3`, `public_s3`); you usually do not need manual spans around S3 calls.
- **systematic-debugging** — when spans are missing, check in order: `OTEL_SDK_DISABLED`, then which process initialised the provider (`apps.py` vs `celery.py`), then collector connectivity at `OTEL_EXPORTER_OTLP_ENDPOINT`, then Jaeger UI at `SMOKE_JAEGER_BASE_URL`.
- **pytest-django-patterns** — `settings/test.py` disables OTel; tests never need to patch tracing.
