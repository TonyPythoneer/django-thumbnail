# Thumbnail Worker — Task Breakdown

> **Session continuity note**: This file is the single source of truth for implementation.
> Pick up any task by status. Completed tasks are marked ✅, in-progress 🔄, not started ⬜.

---

## Architecture Decision Log

### Worker: Celery (Redis broker)
Django 6 built-in `django.tasks` only ships `ImmediateBackend` + `DummyBackend` — no Redis,
no worker process. Celery with Redis broker is the correct production choice.
Worker: `celery -A django_thumbnail worker -l info`. Tasks use `@shared_task`.

### API: Plain Django views (no DRF)
6 simple endpoints, known users only, no complex serializer reuse. `JsonResponse` +
`@require_http_methods` is sufficient. DRF overhead not justified here.

### Storage: MinIO via django-storages (S3-compatible)
`django-storages[s3]` uses `boto3` under the hood and works with MinIO out of the box by overriding
the endpoint URL. No separate MinIO SDK needed.

### Observability: OpenTelemetry → Jaeger
`opentelemetry-sdk` + `opentelemetry-exporter-otlp-proto-grpc` sends traces to Jaeger (already in
docker-compose on port 4317). Instrument Django requests and Celery tasks manually.

### Auth: Django built-in session auth
No JWT, no DRF. Pre-built accounts, cookie session. Images scoped to `request.user`.
Use `@login_required` decorator on views.

### Frontend: django-bootstrap5 + minimal templates
Bootstrap 5 via `django-bootstrap5`. Three pages: login, upload/gallery, task status table.

---

## Stack & Dependencies to Install

```toml
# Add to pyproject.toml dependencies
dependencies = [
    "django>=6.0.5",
    "django-storages[s3]",       # MinIO/S3
    "Pillow",                    # thumbnail generation
    "psycopg[binary]",           # PostgreSQL driver
    "django-bootstrap5",
    "opentelemetry-sdk",
    "opentelemetry-exporter-otlp-proto-grpc",
    "opentelemetry-instrumentation-django",
    "psutil",                    # CPU/memory metrics in task spans
]
```

---

## Infrastructure (docker-compose.yml)

Already present: PostgreSQL 17, Redis 7, Jaeger all-in-one.

**Add MinIO** to docker-compose:

```yaml
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  ports:
    - "9000:9000"   # S3 API
    - "9001:9001"   # MinIO Console UI
  volumes:
    - minio_data:/data
  healthcheck:
    test: ["CMD", "mc", "ready", "local"]
    interval: 5s
    timeout: 5s
    retries: 5
```

Also add `minio_data:` under `volumes:`.

---

## Database Schema

### `images_image` table

| Field               | Type            | Notes                                    |
|---------------------|-----------------|------------------------------------------|
| `id`                | UUID PK         | `default=uuid4`                          |
| `user`              | FK → User       | `on_delete=CASCADE`                      |
| `original_filename` | CharField       | original upload name                     |
| `original_key`      | CharField       | S3/MinIO object key                      |
| `thumbnail_key`     | CharField       | S3/MinIO object key, blank until done    |
| `size_variant`      | CharField       | `small` / `medium` / `large` / `custom` |
| `file_size`         | BigIntegerField | bytes                                    |
| `created_at`        | DateTimeField   | `auto_now_add`                           |

### `images_imagetask` table

| Field            | Type          | Notes                                         |
|------------------|---------------|-----------------------------------------------|
| `id`             | UUID PK       | `default=uuid4`                               |
| `image`          | FK → Image    | `on_delete=CASCADE`, `related_name="tasks"`   |
| `celery_task_id` | CharField     | latest Celery task ID                         |
| `status`         | CharField     | `pending` / `processing` / `done` / `failed` |
| `error_message`  | TextField     | blank unless failed                           |
| `created_at`     | DateTimeField | `auto_now_add`                                |
| `updated_at`     | DateTimeField | `auto_now`                                    |

`image.latest_task()` → most recent `ImageTask`. `image.current_status()` → derived from it.
Thumbnail naming: `{original_stem}_thumbnail{ext}`, size 300×300 (preserves aspect ratio).

---

## Placeholder Images

Three pre-built images committed to `images/static/images/placeholders/`:
- `placeholder_small.jpg` — 400×300
- `placeholder_medium.jpg` — 800×600
- `placeholder_large.jpg` — 1920×1080

Generate with Pillow in a management command `generate_placeholders` (solid color + centered text label).

---

## Pre-built Test Accounts

Management command: `create_test_users`

| Email              | Password |
|--------------------|----------|
| test1@example.com  | test1    |
| test2@example.com  | test2    |

Run once after migrate: `uv run python django_thumbnail/manage.py create_test_users`

---

## Settings Structure

```
django_thumbnail/
  django_thumbnail/
    settings/
      __init__.py      # imports base
      base.py          # common settings
      local.py         # dev overrides (sqlite → postgres, DEBUG=True)
```

Key env vars (use python-decouple or os.environ):

| Var                    | Default (dev)              |
|------------------------|----------------------------|
| `DATABASE_URL`         | `postgres://django_thumbnail:django_thumbnail@localhost:5432/django_thumbnail` |
| `REDIS_URL`            | `redis://localhost:6379/0` |
| `MINIO_ENDPOINT`       | `localhost:9000`           |
| `MINIO_ACCESS_KEY`     | `minioadmin`               |
| `MINIO_SECRET_KEY`     | `minioadmin`               |
| `MINIO_BUCKET_NAME`    | `thumbnails`               |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` |

---

## API Endpoints

Base path: `/api/`

### Tasks (`/api/tasks/`)

| Method | URL                      | Auth | Description                    |
|--------|--------------------------|------|--------------------------------|
| POST   | `/api/tasks/`            | ✓    | Create task for an image       |
| GET    | `/api/tasks/{task_id}/`  | ✓    | Get task status + result       |
| DELETE | `/api/tasks/{task_id}/`  | ✓    | Cancel/revoke task             |

POST body: `{ "image_id": "<uuid>" }`
Response includes: `task_id`, `status`, `image_id`, `thumbnail_url` (when done)

### Images (`/api/images/`)

| Method | URL                        | Auth | Description                   |
|--------|----------------------------|------|-------------------------------|
| GET    | `/api/images/`             | ✓    | List user's own images        |
| POST   | `/api/images/`             | ✓    | Upload image (multipart)      |
| DELETE | `/api/images/{image_id}/`  | ✓    | Delete image + S3 objects     |

POST body: `multipart/form-data` with `file` + `size_variant` fields.

### Auth

| Method | URL          | Description  |
|--------|--------------|--------------|
| POST   | `/api/auth/login/`  | Session login |
| POST   | `/api/auth/logout/` | Session logout |

---

## Celery Task

```python
# images/tasks.py
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def generate_thumbnail(self, image_task_id: str) -> None: ...
```

Enqueue: `generate_thumbnail.delay(str(image_task.id))`

Steps inside task:
1. Fetch `Image` record, set `status=processing`
2. Download original from MinIO → in-memory `BytesIO`
3. Pillow resize to 300×300 (thumbnail, preserving aspect ratio)
4. Upload thumbnail to MinIO
5. Update `Image`: `status=done`, `thumbnail_key=...`
6. Emit OTel span with attributes: `task_id`, `image_id`, `user_id`, `image_name`,
   `duration_ms`, CPU/memory via `psutil`
7. On exception: set `status=failed`, `error_message`

---

## OpenTelemetry Instrumentation

File: `django_thumbnail/telemetry.py` — call `setup_telemetry()` from `AppConfig.ready()`.

Spans to record:

| Span name                  | Attributes                                                    |
|----------------------------|---------------------------------------------------------------|
| `http.request`             | auto via `opentelemetry-instrumentation-django`               |
| `celery.task.generate_thumbnail` | `task_id`, `image_id`, `user_id`, `image_name`, `status`, `duration_ms`, `cpu_percent`, `memory_mb` |
| `minio.upload`             | `bucket`, `key`, `size_bytes`                                 |

---

## HTML Pages

All pages require login except `/login/`.

| URL          | Template                  | Description                                      |
|--------------|---------------------------|--------------------------------------------------|
| `/login/`    | `auth/login.html`         | Username/password form                           |
| `/`          | `images/gallery.html`     | Table of images + status + thumbnail preview     |
| `/upload/`   | `images/upload.html`      | Size picker (small/med/large) OR file upload     |

Gallery table columns: Filename, Size Variant, Status, Thumbnail Preview, Created, Actions (delete / retry).
Polling: JS `setInterval` every 3s to refresh status for `pending`/`processing` rows via GET `/api/tasks/{id}/`.

---

## Tests

### API Tests (`images/tests/test_api.py`)
- Upload image → assert 201, record created in DB
- Get task status → assert correct fields
- Delete image → assert 204, S3 objects cleaned up
- Auth: unauthenticated requests → 403
- Cross-user isolation: user2 cannot access user1's images

### Task Tests (`images/tests/test_tasks.py`)
- `generate_thumbnail` with mocked MinIO (`unittest.mock.patch`) → assert thumbnail uploaded, status=done
- Failure path: MinIO raises exception → assert status=failed, error_message set
- Use `django-storages` `InMemoryStorage` backend in test settings to avoid real MinIO calls
- Use `CELERY_TASK_ALWAYS_EAGER = True` in test settings so tasks run synchronously

### Benchmark (`images/tests/test_benchmark.py`)
- Use `time.perf_counter` around API calls (not a load test, just timing baseline)
- Upload 10 images sequentially, record p50/p95 of upload + task completion time
- Print results to stdout (no assertions, just diagnostic)

---

## Implementation Task List

### Phase 0 — Infrastructure ✅
- [x] **0.1** Add MinIO to `docker-compose.yml`
- [x] **0.2** Install all dependencies via `uv add`
- [x] **0.3** Split settings into `settings/base.py` + `settings/local.py`
- [x] **0.4** Configure PostgreSQL, Redis, MinIO, Celery, OTEL in settings
- [x] **0.5** Makefile with `make dev/migrate/worker/up/down/logs`

### Phase 1 — Django App Skeleton ✅
- [x] **1.1** Create Django app: `python manage.py startapp images`
- [x] **1.2** Define `Image` + `ImageTask` models, run makemigrations + migrate
- [x] **1.3** Register models in Django admin
- [x] **1.4** Management command `create_test_users`
- [x] **1.5** Management command `generate_placeholders` (Pillow, writes to static)
- [x] **1.6** Management command `createbucket` (create MinIO bucket on startup)

### Phase 2 — Storage & Celery ✅
- [x] **2.1** Configure `django-storages` with MinIO endpoint in settings
- [x] **2.2** Implement `generate_thumbnail` Celery task in `images/tasks.py`
- [x] **2.3** Verify task imports cleanly via Django shell

### Phase 3 — Observability ⬜
- [ ] **3.1** `telemetry.py`: init OTel TracerProvider, OTLP gRPC exporter → Jaeger
- [ ] **3.2** Django auto-instrumentation in `AppConfig.ready()`
- [ ] **3.3** Manual span in `generate_thumbnail` with all required attributes
- [ ] **3.4** Manual span around MinIO upload/download calls
- [ ] **3.5** Verify traces appear in Jaeger UI at http://localhost:16686

### Phase 4 — API Views ⬜
- [ ] **4.1** `images/views.py`: image list, upload, delete (`JsonResponse` + `@login_required`)
- [ ] **4.2** `images/views.py`: task create, status, cancel
- [ ] **4.3** `images/views.py`: login/logout views (session-based)
- [ ] **4.4** Wire up `images/urls.py`, include in root `urls.py`
- [ ] **4.5** Owner check: filter all querysets by `request.user`

### Phase 5 — HTML Frontend ⬜
- [ ] **5.1** Install `django-bootstrap5`, add to `INSTALLED_APPS`
- [ ] **5.2** `base.html`: Bootstrap 5 navbar (user email + logout), block structure
- [ ] **5.3** `auth/login.html`: login form
- [ ] **5.4** `images/upload.html`: size picker radio + file input + submit
- [ ] **5.5** `images/gallery.html`: table with status badge + thumbnail `<img>`
- [ ] **5.6** JS polling in gallery: refresh status cells every 3s for non-done rows

### Phase 6 — Tests ⬜
- [ ] **6.1** Test settings (`settings/test.py`): InMemoryStorage, `CELERY_TASK_ALWAYS_EAGER`, dummy OTEL
- [ ] **6.2** API tests: upload, get status, delete, auth, cross-user isolation
- [ ] **6.3** Task tests: success path (mocked MinIO), failure path (retry)
- [ ] **6.4** Benchmark script

---

## File Layout (target)

```
django_thumbnail/
├── manage.py
├── django_thumbnail/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── local.py
│   │   └── test.py
│   ├── celery.py
│   ├── telemetry.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── images/
    ├── apps.py
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── tasks.py            # Celery @shared_task definitions
    ├── storage.py          # MinIO helpers
    ├── management/
    │   └── commands/
    │       ├── create_test_users.py
    │       ├── generate_placeholders.py
    │       └── createbucket.py
    ├── templates/
    │   ├── base.html
    │   ├── auth/login.html
    │   └── images/
    │       ├── gallery.html
    │       └── upload.html
    ├── static/images/placeholders/
    │   ├── placeholder_small.jpg
    │   ├── placeholder_medium.jpg
    │   └── placeholder_large.jpg
    └── tests/
        ├── test_api.py
        ├── test_tasks.py
        └── test_benchmark.py
```

---

## Quick Start (after picking up this file)

```bash
docker compose up -d          # postgres, redis, jaeger, minio
uv run migrate
uv run python django_thumbnail/manage.py create_test_users
uv run python django_thumbnail/manage.py generate_placeholders
uv run python django_thumbnail/manage.py createbucket
make worker &                 # celery -A django_thumbnail worker -l info
uv run dev                    # django runserver
```

Login at http://localhost:8000/login/ with `test1@example.com` / `test1`.
Jaeger UI at http://localhost:16686.
MinIO Console at http://localhost:9001 (minioadmin/minioadmin).
