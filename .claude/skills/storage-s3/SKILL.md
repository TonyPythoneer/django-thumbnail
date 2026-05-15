---
name: storage-s3
description: S3/MinIO storage patterns for django-thumbnail — boto3 client construction, InternalS3 vs PublicS3 singletons, bucket management, and MinIO endpoint configuration. Use when working with S3/MinIO storage, modifying images/storage.py, managing buckets, or implementing upload/download flows.
---

# S3 / MinIO Storage Patterns

This project talks to MinIO directly via `boto3` — **no `django-storages`** (CLAUDE.md §0/§2). All S3 access flows through two singletons in `images/storage.py`: `internal_s3` for server-side I/O and `public_s3` for browser-facing presigned URLs. The two-client split exists because the worker reaches MinIO over the Docker network (`http://minio:9000`) while the browser must hit a host-reachable URL (`http://localhost:9000`).

## When to Use

Apply this skill when:
- Adding or changing S3 reads/writes in `images/storage.py`, `images/tasks.py`, `images/models.py`, or `images/views.py`
- Touching MinIO env vars (`AWS_*`) in `django_thumbnail/settings/base.py` or `docker-compose.yml`
- Modifying or adding management commands under `images/management/commands/` that touch the bucket (`create_bucket`, `clean_bucket`)
- Wiring presigned upload/download flows for the browser
- Writing tests that mock storage — the patch targets follow the import path of the singleton

## Core Patterns

### Two singletons, two endpoints

`images/storage.py` exposes exactly two module-level instances at the bottom of the file:

```python
internal_s3 = InternalS3()
public_s3 = PublicS3()
```

Both inherit from `_S3BaseClient`, which constructs a single `boto3.client("s3", ...)` with `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` from `django.conf.settings`. They differ only in **endpoint** and **signature config**:

| Class       | Endpoint setting              | Purpose                                                        | Methods                                  |
| ----------- | ----------------------------- | -------------------------------------------------------------- | ---------------------------------------- |
| `InternalS3` | `AWS_S3_ENDPOINT_URL`         | Server-side I/O from Django/Celery (worker ↔ MinIO over Docker network) | `download(bucket, key)`, `upload(bucket, key, data)`, `delete(bucket, key)` |
| `PublicS3`   | `AWS_S3_PUBLIC_ENDPOINT_URL`  | Generates presigned URLs the **browser** will hit (must resolve from the user's machine) | `presign_get(key)`, `presign_put(key)`   |

`PublicS3` also forces `Config(signature_version=settings.AWS_S3_PUBLIC_SIGNATURE_VERSION)` — `"s3v4"` is required by MinIO for presigned URLs.

**Rule of thumb**: if the bytes flow through Python, use `internal_s3`. If a URL is going into a template / JSON response for the browser, use `public_s3`.

Real call sites:
- `images/tasks.py` — `internal_s3.download` / `internal_s3.upload` inside `generate_thumbnail`
- `images/models.py` — `internal_s3.upload` / `internal_s3.delete` for original-image lifecycle; `public_s3.presign_get` to expose URLs in API payloads
- `images/views.py` — `public_s3.presign_put` for direct browser uploads, `public_s3.presign_get` for display URLs

### boto3 client construction (singleton, NOT per-call)

The clients are **constructed once at module import** (`internal_s3 = InternalS3()` at the bottom of `images/storage.py`). `boto3.client("s3", ...)` is expensive (auth handler chain, signer setup); creating one per request or per task tanks throughput.

**Do**:
- Import the singletons: `from images.storage import internal_s3, public_s3`
- Add new operations as methods on `InternalS3` / `PublicS3` so they share the underlying `self._client`
- Read credentials/endpoints from `django.conf.settings` inside `__init__` (already done in `_S3BaseClient`)

**Do not**:
- Call `boto3.client("s3", ...)` ad-hoc in views/tasks/models — that bypasses the singleton and re-pays construction cost
- Reach into `internal_s3._client` from production code (the leading underscore is intentional). Tests may do so as a last resort — see `images/tests/test_smoke.py` which uses `internal_s3._client.head_object(...)` for assertion-only existence checks
- Hardcode `endpoint_url`, access key, or secret anywhere — they live in settings only

### MinIO endpoint configuration (env vars from settings)

All S3 settings are read in `django_thumbnail/settings/base.py` under `── S3 / MinIO ──`:

```python
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "thumbnails")
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL", "http://localhost:9000")
AWS_S3_PUBLIC_ENDPOINT_URL = os.environ.get("AWS_S3_PUBLIC_ENDPOINT_URL", AWS_S3_ENDPOINT_URL)
AWS_S3_PUBLIC_SIGNATURE_VERSION = "s3v4"  # minio requires s3v4
```

How the two endpoints are wired in `docker-compose.yml` under `x-app-env`:

```yaml
AWS_S3_ENDPOINT_URL: http://minio:9000          # in-cluster, used by InternalS3
AWS_S3_PUBLIC_ENDPOINT_URL: http://localhost:9000  # host-reachable, used by PublicS3 for presigned URLs
```

The fallback `AWS_S3_PUBLIC_ENDPOINT_URL = ... AWS_S3_ENDPOINT_URL` makes local-laptop dev (no Docker) work with a single value. When adding a new deployment env (staging/prod), set both explicitly.

`AWS_STORAGE_BUCKET_NAME` is read directly by callers, e.g. `internal_s3.upload(settings.AWS_STORAGE_BUCKET_NAME, key, data)` and inside `PublicS3.presign_get/put`. The singleton does **not** capture a bucket — bucket name stays an explicit argument so the same client could be reused across buckets later.

### Bucket management commands

Two `manage.py` commands handle the bucket lifecycle in dev/CI. Both live in `images/management/commands/` and use a `cached_property` to build a one-off `boto3.client("s3", ...)`. They intentionally bypass `internal_s3` because a fresh process for a CLI invocation doesn't benefit from the singleton.

- `create_bucket.py` — idempotent: `head_bucket(Bucket=...)` first; on `ClientError`, `create_bucket(Bucket=...)`. Wired into Compose `init` service so a fresh `docker compose up` always has the bucket. Run via `make create-bucket` (see `Makefile`), never `python manage.py create_bucket` directly (CLAUDE.md §0).
- `clean_bucket.py` — wipes every object: `list_objects_v2` + per-key `delete_object`. Use for test/dev resets. There is no pagination handling (current bucket is small), so if the bucket grows beyond `MaxKeys=1000` this needs `Paginator`.

When adding a new bucket-level operation (lifecycle policy, CORS, versioning), prefer a new management command following this same `cached_property` + `BaseCommand` shape over inlining boto3 in app code.

### Upload / download flow shape

Two distinct upload paths exist; pick the right one:

1. **Server-mediated upload** (`Image.save_original` in `images/models.py`) — bytes arrive at Django, model calls `internal_s3.upload(settings.AWS_STORAGE_BUCKET_NAME, self.original_key, data)`. Use for small payloads or when Django needs to inspect the bytes.
2. **Presigned PUT** (`images/views.py` upload view) — Django returns `public_s3.presign_put(image.original_key)`; the browser PUTs directly to MinIO. Use for large files / to avoid proxying through Django.

Downloads inside the worker always use `internal_s3.download(bucket, key) -> io.BytesIO`. Browser-facing download/display URLs are `public_s3.presign_get(key)` with a 1-hour TTL (`_PRESIGN_EXPIRES_IN = 3600` on `PublicS3`).

## Anti-Patterns

- Constructing `boto3.client("s3", ...)` inline in a view, task, or model — go through `internal_s3` / `public_s3`. Exception: one-shot management commands following the `create_bucket` / `clean_bucket` pattern.
- Hardcoding `http://minio:9000` / `http://localhost:9000` / `minioadmin` anywhere outside `settings/base.py` (defaults) and `docker-compose.yml` (env values).
- Using `internal_s3` to mint URLs for the browser — the URL embeds the in-cluster hostname (`minio:9000`) and won't resolve from the user's machine. Use `public_s3`.
- Adding `django-storages` to dependencies. The project deliberately uses raw `boto3` (CLAUDE.md §2); `django-storages` was rejected.
- Passing the bucket name from the caller as a magic string — read `settings.AWS_STORAGE_BUCKET_NAME` at the call site.
- Reaching into `internal_s3._client` from production code. If you need a new low-level S3 operation, add a method on `InternalS3` / `PublicS3` instead.
- Forgetting `signature_version="s3v4"` on a new presigning client — MinIO rejects v2 presigned URLs.
- Patching `boto3` itself in tests. Patch the singleton method instead: `patch("images.tasks.internal_s3.download", ...)` or `patch("images.storage.public_s3.presign_put", ...)`. The patch target follows the **import path** of the caller.

## Integration with Other Skills

- **celery-patterns** — `generate_thumbnail` is the canonical `internal_s3` consumer; idempotency depends on the deterministic `{stem}_thumbnail{ext}` key from `Image.create_with_key`. When patching in task tests, target `images.tasks.internal_s3.*` (not `images.storage.*`).
- **django-models** — `Image.upload_original` / `Image.delete_from_storage` encapsulate S3 side effects so views/tasks never touch the bucket directly; presigned URLs are materialized in `Image.to_dict` / `ImageTask.to_dict` for API responses.
- **pytest-django-patterns** — eager Celery (`settings/test.py`) plus singleton patching means storage tests don't need a real MinIO. Smoke tests in `images/tests/test_smoke.py` are the exception and do hit the live bucket.
- **systematic-debugging** — when uploads succeed from Django but browser URLs 404, the first hypothesis is endpoint confusion: check `AWS_S3_PUBLIC_ENDPOINT_URL` resolves from the user's machine, not just from inside Docker.
