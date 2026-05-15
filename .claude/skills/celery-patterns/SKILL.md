---
name: celery-patterns
description: Celery task patterns for django-thumbnail — @shared_task convention, retry with exponential backoff, idempotency, and Image/ImageTask state flow. Use when writing Celery tasks, designing retry strategies, debugging task failures, or implementing async background work.
---

# Celery Task Patterns

This project uses Celery + Redis broker for async work. `django.tasks` has no Redis backend — always use Celery. The canonical example is `generate_thumbnail` in `images/tasks.py`.

## When to Use

Apply this skill when:
- Adding a new `@shared_task` to `images/tasks.py` or a future app's `tasks.py`
- Changing the retry strategy or `max_retries` of an existing task
- Debugging stuck/failed tasks via `ImageTask` rows
- Wiring a task call site (use `ImageTask.create_and_dispatch()`, never call `.delay()` directly from a view)
- Writing tests that exercise tasks (eager mode is on in `django_thumbnail/settings/test.py`)

## Core Patterns

### `@shared_task` convention

- Always use `@shared_task` (decoupled from a specific app), never `@app.task`.
- For tasks that retry or need their Celery request context, set `bind=True` and accept `self` as the first arg.
- Declare `max_retries` explicitly — do not rely on Celery's default.
- The Celery app is configured in `django_thumbnail/celery.py` with `app.autodiscover_tasks()`; new task modules must live in an installed app under `<app>/tasks.py` to be picked up.

Real signature from `images/tasks.py`:

```python
@shared_task(bind=True, max_retries=3)
def generate_thumbnail(self, image_task_id: str) -> None:
    ...
```

### Idempotency (CLAUDE.md §5.5)

**Rule**: every Celery task must be safe to retry. A retry must produce the same final state as a first successful run.

**Why**: Celery may re-deliver a message after broker hiccups, worker restarts, or explicit `self.retry()`. A non-idempotent task corrupts data on the second run (double-charged, duplicate rows, partially-written objects).

**How `generate_thumbnail` achieves idempotency**:
- Re-downloads `image.original_key` from MinIO every attempt — no local state assumed.
- Writes thumbnail to a **deterministic** S3 key (`image.thumbnail_key`, computed once at `Image.create_with_key` time as `{stem}_thumbnail{ext}`). Re-running overwrites the same object; no duplicate keys accumulate.
- State transitions go through `ImageTask.mark_processing` / `mark_done` / `mark_failed`, all of which are `save(update_fields=[...])` on a row keyed by `image_task_id` — re-entering `PROCESSING` is a no-op.
- The task takes an `ImageTask` ID (not a freshly-created row) so a retry operates on the same `ImageTask`, never spawns a new one.

**Checklist for new tasks**:
- [ ] All writes target deterministic keys / primary keys (no `uuid4()` mid-task for a value the task will re-write).
- [ ] No "create row if it doesn't exist" without `get_or_create` or a unique constraint.
- [ ] External side-effects (S3 upload, email, webhook) either are themselves idempotent or are guarded by a status check.
- [ ] Final DB state is computed from inputs, not from "current value + delta".

### Retry with exponential backoff

The project standard is `countdown=2**self.request.retries` inside `self.retry(...)`:

```python
except Exception as exc:
    if self.request.retries >= self.max_retries:
        task.mark_failed(str(exc))
    raise self.retry(exc=exc, countdown=2 ** self.request.retries) from exc
```

Notes:
- `self.request.retries` is the **current** retry count (0 on first attempt), so backoffs are 1s, 2s, 4s for `max_retries=3`.
- Always `raise self.retry(...)` — never call it as a plain function; the raise is what hands control back to Celery.
- Distinguish *permanent* errors (e.g. `InvalidImageError` — bad bytes, no point retrying) from *transient* errors. Permanent errors mark the `ImageTask` as `FAILED` and do **not** retry. See `images/tasks.py` for the two-branch pattern.
- Record the final outcome on the OTel span via `span.set_attributes(dict)` in `finally` — batched, not one call per key.

### Pass IDs, not model instances

**Never** pass a model instance to `.delay()` / `.apply_async()`. Pass the primary key (string for UUIDs) and `.get()` inside the task.

Why:
- Celery serializes args as JSON; model instances would pickle stale field values.
- The DB row may have changed between enqueue and execution — re-fetching gets current state.
- IDs survive worker restarts and replay cleanly.

Real call site (`ImageTask.create_and_dispatch` in `images/models.py`):

```python
task = cls.objects.create(image=image)
async_result = generate_thumbnail.delay(str(task.id))  # UUID -> str
```

Real task body re-fetches with `select_related` to avoid an N+1 on `task.image`:

```python
task = ImageTask.objects.select_related("image").get(id=image_task_id)
```

### `Image` / `ImageTask` state flow

The project splits `Image` (the artifact) from `ImageTask` (one attempt to process it). **A retry creates a NEW `ImageTask` row.** This keeps full history and keeps `Image` clean.

`ImageStatus` (`images/models.py`) values:
`PENDING` → `PROCESSING` → `DONE` | `FAILED`

`ImageTask` fields you will touch:
- `id` (UUID, PK)
- `image` (FK → `Image`, `related_name="tasks"`)
- `celery_task_id` (str) — populated by `mark_processing(celery_id)`
- `status` (`ImageStatus` choices)
- `error_message` (str) — populated by `mark_failed(error)`
- `created_at`, `updated_at`

**State helpers on `ImageTask`** (use these, do not set fields directly):
- `mark_processing(celery_task_id)` — entry of `generate_thumbnail`
- `mark_done()` — happy path
- `mark_failed(error)` — permanent failure or final retry exhaustion

**The retry-as-new-row rule**:
- A *Celery-level* retry of the same task (via `self.retry`) reuses the same `ImageTask` row — it is still the same attempt from the user's perspective.
- A *user-initiated* re-process (e.g. "Try again" button) calls `ImageTask.create_and_dispatch(image)` which creates a brand-new `ImageTask` row. `Image.current_status()` always reads from `latest_task()` (ordered `-created_at`), so the UI naturally reflects the newest attempt.

Owner isolation still applies: any view that triggers a task must first scope the `Image` lookup with `Image.objects.for_user(request.user)` before calling `create_and_dispatch`.

## Anti-Patterns

- Passing a Django model instance to `.delay()` — pass `str(obj.id)` instead.
- Calling `.delay()` directly from a view — go through `ImageTask.create_and_dispatch()` so the `ImageTask` row exists before the worker picks up the message.
- Mutating `ImageTask.status` directly (`task.status = "done"; task.save()`) — use `mark_done()` / `mark_failed()` / `mark_processing()` so `update_fields` stays correct and `updated_at` refreshes.
- Using `@app.task` instead of `@shared_task`.
- Forgetting `bind=True` and then trying to access `self.request.retries`.
- Catching every exception, marking failed, and *also* retrying — pick one branch per exception class.
- Non-idempotent side effects: appending to a list, incrementing without `F()`, uploading to a random key per attempt.
- Setting span attributes one-by-one — use `span.set_attributes({...})`.

## Testing Celery Tasks

Tests run with eager execution configured in `django_thumbnail/settings/test.py`:

```python
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

Effects:
- `generate_thumbnail.delay(...)` runs **synchronously** in the test process. No Redis or worker needed.
- Exceptions inside the task propagate to the test (because of `EAGER_PROPAGATES`), so `pytest.raises` works directly on `.delay()` / `create_and_dispatch()` call sites.
- `self.retry(...)` still raises `Retry` in eager mode — assert task status (`mark_failed` was called) rather than counting retry attempts when verifying terminal behavior.

Patterns:
- Drive the task through its real entry point: call `ImageTask.create_and_dispatch(image)` and then `task.refresh_from_db()` to assert final status. This also exercises the call-site contract.
- For storage failures, patch `images.storage.internal_s3` (the module-level singleton imported in `images/tasks.py`). Do not patch Celery internals.
- For permanent-failure paths (`InvalidImageError`), feed bytes that `PIL.Image.open` rejects and assert `status == ImageStatus.FAILED` with a non-empty `error_message`.
- OTel is disabled in tests (`OTEL_SDK_DISABLED = True`); `trace.get_current_span()` returns a no-op span, so tracing code is safe to leave in the task path.

## Integration with Other Skills

- **django-models** — `Image` / `ImageTask` schema, `ImageQuerySet.for_user`, fat-model patterns (`create_with_key`, `create_and_dispatch`, the `mark_*` helpers).
- **pytest-django-patterns** — Factory Boy factories for `Image` / `ImageTask`, fixtures for authenticated users, AAA structure around the eager-task call.
- **systematic-debugging** — when a task is silently stuck, start from the `ImageTask` row (`status`, `celery_task_id`, `error_message`, `updated_at`) before opening worker logs; reproduce locally with `CELERY_TASK_ALWAYS_EAGER` before chasing broker issues.
