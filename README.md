# Django Thumbnail Worker

A side project demonstrating an end-to-end async image processing pipeline with **distributed tracing across web, worker, and object storage**. Upload an image → Django persists it to MinIO → Celery generates a thumbnail → status surfaced back to the user — every hop stitched into a single trace in Jaeger.

The point of this repo is not the thumbnail. It is the **plumbing around it**: clean domain modeling, owner isolation, retry semantics, and observability that actually works across process boundaries.

---

## Highlights

### 🔭 Distributed tracing that survives every boundary
A single `trace_id` flows from the HTTP request through `apply_async`, into the Celery worker, down into S3/MinIO calls — with correct parent/child nesting. Getting this right required fixing four separate root-cause bugs in OpenTelemetry wiring; the post-mortem lives in [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md) and is the most valuable artifact in this repo.

```
[app]    POST /api/tasks/
[app]    └─ apply_async/generate_thumbnail        ← traceparent injected here
[worker]    └─ run/generate_thumbnail              ← extracted, parented
[worker]       └─ celery.task.generate_thumbnail
[worker]          ├─ minio.download → S3.GetObject
[worker]          └─ minio.upload   → S3.PutObject
```

### 🧱 Clean domain model: `Image` + `ImageTask` split
Image and its processing lifecycle are separate aggregates. A retry creates a new `ImageTask` row — full audit history, the `Image` record stays clean. Owner isolation enforced at the QuerySet layer (`Image.objects.for_user(request.user)`).

### 🔁 Idempotent Celery tasks with structured outcomes
`generate_thumbnail` distinguishes between `DONE` / `INVALID` (don't retry) / `RETRY` (exponential backoff) — span attributes carry the outcome so traces are queryable by failure mode.

### 🔐 Pre-signed URL preview, no public bucket
Thumbnails served via short-lived S3 pre-signed URLs scoped per-user. No anonymous reads against MinIO.

### 🧪 Real-Postgres CI, in-memory storage for unit tests
`settings/test.py` swaps storage to `InMemoryStorage` and forces `CELERY_TASK_ALWAYS_EAGER` — tests run without MinIO, Redis, or Jaeger. CI spins up only Postgres as a service container.

---

## Stack

| Layer | Tech |
|---|---|
| Web | Django 6, `django-bootstrap5` |
| Async | Celery + Redis broker, `@shared_task` |
| Storage | `boto3` → MinIO (S3-compatible) |
| Database | PostgreSQL 17 |
| Tracing | OpenTelemetry SDK → OTLP gRPC → Jaeger all-in-one |
| Tooling | `uv`, `ruff`, `pytest-django`, `factory-boy` |
| CI | GitHub Actions |

---

## Quick start

```bash
make up        # build + start full stack: db, redis, minio, jaeger, web (:8000), worker
make smoke     # upload → dispatch → poll status (requires the stack from `make up`)

open http://localhost:16686   # Jaeger UI — full nested trace
open http://localhost:8000    # login as test1@example.com / test1
```

`make up` builds the app image and runs the `init` container — migrations, MinIO
bucket creation, and test-account seeding — then starts the web and worker
containers. `make up-infra` starts infra only; `make down` stops everything;
`make logs-app` / `make logs-infra` tail logs.

Test accounts seeded automatically: `test1@example.com` / `test1`, `test2@example.com` / `test2`.

---

## Repository layout

```
django-thumbnail/
├── manage.py
├── Makefile · docker-compose.yml · Dockerfile.dev · pyproject.toml
├── django_thumbnail/
│   ├── settings/
│   │   ├── base.py          env-driven config
│   │   ├── local.py
│   │   └── test.py          eager Celery, OTel disabled
│   ├── celery.py            Celery app + worker telemetry signal
│   └── telemetry.py         OTel TracerProvider setup
├── images/                  the only app
│   ├── models.py            Image, ImageTask, ImageStatus
│   ├── tasks.py             generate_thumbnail (idempotent, retrying)
│   ├── apps.py              Django app config
│   ├── utils.py             S3 helpers (direct put/get, no s3transfer threads)
│   ├── views.py             plain JsonResponse, @login_required
│   ├── management/commands/ create_bucket, create_test_users, clean_*, ...
│   └── tests/               pytest-django + factory-boy
├── docs/OBSERVABILITY.md    ★ the trace-stitching post-mortem
└── .github/workflows/       ci-app-integration-test.yml, ci-smoke-test.yml
```

---

## Design decisions worth calling out

- **No DRF.** Plain `JsonResponse` + `@login_required` — small surface, less magic.
- **Direct boto3 `put_object` / `get_object`** instead of `upload_fileobj` — avoids `s3transfer` thread hops that break OTel context propagation. See [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md) Symptom 2.
- **`SimpleSpanProcessor` in dev**, `BatchSpanProcessor` in prod — dev workflow needs spans visible immediately even on `SIGTERM`.
- **Programmatic OTel init in `apps.py:ready()`** instead of the `opentelemetry-instrument` CLI wrapper — the wrapper accessed `django.conf.settings` before `DJANGO_SETTINGS_MODULE` was applied, breaking `runserver`.
- **`make` is the only entry point.** `manage.py` is never invoked directly so env vars (OTEL service name, settings module) are always consistent.

---

## Further reading

- [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md) — five symptoms, five root causes, one working distributed trace
- [`tasks/refinement/`](tasks/refinement/) — refinement plan & numbered checklists
- [`CLAUDE.md`](CLAUDE.md) — context for AI-assisted development
