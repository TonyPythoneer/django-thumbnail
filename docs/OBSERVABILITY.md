# Django Thumbnail Worker — Observability Notes

This document explains how the distributed trace was assembled across the Django web process, the Celery worker, and MinIO/S3 calls, and what went wrong before the final fix.

---

## Target topology

One logical user action (`POST /api/tasks/`) crosses three runtime boundaries:

```
[django-thumbnail-app]    POST api/tasks/                       (HTTP entry)
[django-thumbnail-app]    └─ apply_async/generate_thumbnail     (Celery publish)
[django-thumbnail-worker]    └─ run/generate_thumbnail          (Celery consume)
[django-thumbnail-worker]       └─ celery.task.generate_thumbnail   (manual span)
[django-thumbnail-worker]          ├─ minio.download            (manual span)
[django-thumbnail-worker]          │  └─ S3.GetObject           (boto3 auto)
[django-thumbnail-worker]          └─ minio.upload              (manual span)
[django-thumbnail-worker]             └─ S3.PutObject           (boto3 auto)
```

Goal: a single `trace_id` shared across every span above, with correct parent/child relationships, and two distinct `service.name` resources so Jaeger separates app vs worker visually.

---

## Symptom 1 — Worker trace was a separate root

**What we saw.** Jaeger had a `POST api/tasks/` trace with two spans (HTTP root + `apply_async`) and a *different* trace starting at `run/generate_thumbnail`. No parent link.

**Why.**
`opentelemetry-instrumentation-celery` injects a `traceparent` header into the Celery message *only* if the instrumentor has been activated in the **publisher** process. The Django process had `DjangoInstrumentor` wired in `apps.py:ready()`, but `CeleryInstrumentor` was not. Without it, `apply_async` published a message with no W3C trace context, so the worker (which *did* have `CeleryInstrumentor` active via the `opentelemetry-instrument` wrapper) extracted nothing and started a fresh root span.

**Fix.** Wire `CeleryInstrumentor` programmatically in `images/apps.py:ready()`, alongside `DjangoInstrumentor`. The Django process now patches Celery's `Producer.publish` to inject `traceparent`, and the worker's `CeleryInstrumentor` extracts it on consume — same `trace_id`, correct parent.

```python
# django_thumbnail/images/apps.py
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor

DjangoInstrumentor().instrument()
CeleryInstrumentor().instrument()
```

---

## Symptom 2 — S3 spans were separate root traces

**What we saw.** `S3.PutObject` / `S3.GetObject` appeared in Jaeger as standalone single-span traces, not as children of `minio.upload` / `minio.download` (worker) or `POST api/images/` (Django upload view).

**Why — root cause, not the obvious one.**
`BotocoreInstrumentor` patches `botocore.client.BaseClient._make_api_call`, so every S3 API call *does* produce a span. The problem is **OpenTelemetry context propagation does not cross thread boundaries by default.**

`boto3` exposes two paths for moving bytes:

| API | Internal path | Threading |
|---|---|---|
| `s3.upload_fileobj` / `s3.download_fileobj` | `s3transfer.TransferManager` | Always uses a worker thread pool, even for one-shot small files |
| `s3.put_object` / `s3.get_object` | Direct `_make_api_call` | Single synchronous call on the caller's thread |

When `default_storage.save()` (django-storages) or `s3.upload_fileobj()` runs, the actual `PutObject` HTTP request executes on a `TransferManager` thread. The OTel context (which holds the active parent span) lives in a `ContextVar`. Spawning a thread without an explicit context propagator means the child thread sees an empty context, so `BotocoreInstrumentor` records the span with no parent — a new root.

**Fix.** Switch every S3 byte-moving call to the single-shot, synchronous form:

```python
# Before: spawns a transfer thread, span loses parent
s3.upload_fileobj(buf, bucket, key)
s3.download_fileobj(bucket, key, buf)
default_storage.save(key, file)   # also uses TransferManager under the hood

# After: same thread, context preserved, span nests under caller
s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
obj = s3.get_object(Bucket=bucket, Key=key); body = obj["Body"].read()
```

This eliminates the thread hop and the S3 span becomes a child of whichever span is active on the calling thread (`POST api/images/` for the upload view, `minio.upload` / `minio.download` in the worker).

> Alternative considered: install `opentelemetry-instrumentation-threading` to auto-propagate context across `threading.Thread`. Rejected — adds runtime overhead for every thread spawn project-wide just to fix a localized S3 path. Direct API calls are simpler and remove implicit reliance on `s3transfer`'s threading.

---

## Symptom 3 — `opentelemetry-instrument` wrapper broke `runserver`

**What we saw.** `make dev` failed with `CommandError: You must set settings.ALLOWED_HOSTS if DEBUG is False.` even though `local.py` clearly sets `DEBUG=True` and `ALLOWED_HOSTS=["localhost", "127.0.0.1"]`.

**Why.** `opentelemetry-instrument` activates auto-instrumentors via a sitecustomize hook before `manage.py main()` runs. That hook touches `django.conf.settings` early. Under our configuration, the access path caused `LazySettings._wrapped` to be populated with `global_settings` defaults — `DEBUG=False`, `ALLOWED_HOSTS=[]` — before `DJANGO_SETTINGS_MODULE` was honoured. By the time `manage.py` ran `os.environ.setdefault("DJANGO_SETTINGS_MODULE", ...)`, `_wrapped` was already set and the setdefault did nothing.

**Fix.** Drop the `opentelemetry-instrument` CLI wrapper for `make dev`. Initialize OpenTelemetry **programmatically** inside `images/apps.py:ready()`, which Django invokes after settings are loaded properly. Same approach for the worker — `make worker` no longer uses the wrapper either. The wrapper was redundant given we already call:

```python
setup_telemetry(
    service_name=settings.OTEL_SERVICE_NAME,
    otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
)
DjangoInstrumentor().instrument()
CeleryInstrumentor().instrument()
BotocoreInstrumentor().instrument()
```

---

## Symptom 4 — Spans appeared in Jaeger only sometimes

**What we saw.** After killing the worker via `pkill`, the most recent task's manual spans (`celery.task.generate_thumbnail`, `minio.upload`) sometimes vanished, but their *children* (`S3.PutObject`) still appeared with a dangling parent reference.

**Why.** The default `BatchSpanProcessor` buffers spans in memory and flushes on a timer or buffer threshold. `SIGTERM` from `pkill` did not give it time to flush, so the buffered parent spans were lost while already-flushed children remained.

**Fix.** Switched to `SimpleSpanProcessor` in `telemetry.py` — it exports each span synchronously on `end()`. Trade-off: higher per-span latency. Acceptable for dev. Switch back to `BatchSpanProcessor` for production, where `SIGTERM` handling via `provider.shutdown()` flushes gracefully.

---

## Symptom 5 — All spans appeared under one service `django-thumbnail`

**What we saw.** Jaeger's service dropdown listed one service. Spans from both the web process and the worker were tagged identically, making it hard to read the trace.

**Fix.** Set `OTEL_SERVICE_NAME` per process in the `Makefile`:

```makefile
dev:
	$(DJANGO_ENV) OTEL_SERVICE_NAME=django-thumbnail-app $(MANAGE) runserver

worker:
	cd django_thumbnail && $(DJANGO_ENV) OTEL_SERVICE_NAME=django-thumbnail-worker uv run celery -A django_thumbnail worker -l info
```

`base.py` reads `OTEL_SERVICE_NAME` from the environment and passes it into the `Resource` attached to the `TracerProvider`. Two distinct `service.name` resources, one shared trace.

---

## Why this works end-to-end

1. **Trace ID is generated once** at the HTTP entry by `DjangoInstrumentor` and lives in the OTel context for that request.
2. **`CeleryInstrumentor` on the publisher** serializes the context into a `traceparent` header attached to the Celery message body.
3. **`CeleryInstrumentor` on the consumer** deserializes the header and re-establishes the context inside the worker's task function — the manual span `celery.task.generate_thumbnail` created inside the task inherits this context as its parent.
4. **Manual spans `minio.upload` / `minio.download`** use the active context, so they become children of `celery.task.generate_thumbnail`.
5. **`BotocoreInstrumentor`** wraps every `_make_api_call`, and because we now call `put_object`/`get_object` directly (no thread hop), the S3 span sees the same context and nests under the manual MinIO span.

The whole chain shares one `trace_id`, every parent/child relationship is correct, and the two `service.name` values let Jaeger render the gantt with clear visual separation between web and worker.

---

## Verifying

```bash
make up        # starts postgres, redis, minio, jaeger
make migrate
make dev       # one terminal
make worker    # another terminal
make smoke     # uploads, dispatches task, polls status

open http://localhost:16686
# Service: django-thumbnail-app
# Operation: POST api/tasks/
# Find Traces → click → see the full 8-span nested gantt
```
