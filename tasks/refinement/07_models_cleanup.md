# 07 — Models & settings cleanup

**Lens:** Solution Architect **Risk:** Low **Est. LOC delta:** −15 to −25

## Context

Smaller cleanups in `models.py` and `settings/base.py`. None are bugs; all are
"a reviewer pauses here and shouldn't have to".

1. **Dead `django-storages` config.** `settings/base.py:108-110` sets
   `AWS_S3_ADDRESSING_STYLE`, `AWS_DEFAULT_ACL`, `AWS_QUERYSTRING_AUTH`. These are
   `django-storages` settings — but `django-storages` is **not** a dependency and
   storage is raw `boto3` (`images/utils.py`, becoming `storage.py` in task 03).
   Nothing reads these three settings. Vestigial.

2. **Circular import worked around twice.** `models.py:9` imports from the storage
   module at top level; `ImageTask.create_and_dispatch` (`models.py:133-143`) does
   a *local* import of `generate_thumbnail` to dodge a cycle; `tasks.py:56` does a
   local import of `ImageTask` for the same reason. Two lazy imports pointing at
   each other — a reviewer has to reconstruct the cycle to understand why.

3. **Duplicated `__str__` timestamp logic.** `Image.__str__` (`models.py:38-42`)
   and `ImageTask.__str__` (`models.py:115-117`) both do
   `ts = self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "?"`.

4. **`to_dict()` placement.** `Image.to_dict()` / `ImageTask.to_dict()` are
   serialization logic living on the model. That is a defensible choice for a
   no-DRF project — but see **task 04**: the gallery view *also* serializes
   `Image`. Make sure after task 04 there is one obvious home for serialization.

## Checklist

### Settings
- [x] Delete `AWS_S3_ADDRESSING_STYLE`, `AWS_DEFAULT_ACL`, `AWS_QUERYSTRING_AUTH`
      from `settings/base.py` — grep confirms nothing reads them now.
- [x] Audited `base.py`; no other dead settings spotted.

### Circular import
- [x] Untangle cycle — fat-model kept; only one runtime lazy import remains
      (`models.py:create_and_dispatch` local-imports `generate_thumbnail`).
      `tasks.py` now top-level imports `from .models import Image, ImageTask`
      (no cycle since `models.py` top-level has no `tasks` dependency).
- [x] Comment on remaining lazy import retained.

### `__str__` dedup
- [x] `_fmt_ts(dt) -> str` helper added at `models.py:16`. Both `__str__`
      implementations use it.

### Serialization home
- [x] After **task 04** lands, confirm: is there exactly one discoverable place
      that serializes `Image`? Resolved: two named helpers split by purpose —
      `Image.to_dict()` for the JSON API (uses isoformat strings, no task_id) and
      `views._gallery_row()` for the HTML template context (raw datetime,
      conditional thumbnail, includes `task_id` for HTML polling). No anonymous
      inline dicts remain; each shape has one obvious home.

## Acceptance

- [x] `grep -r AWS_S3_ADDRESSING_STYLE` (and the other two) returns no hits in any
      `.py` / `.toml` / `.yml` / `.md` file — fully purged.
- [x] At most one runtime lazy/deferred import remains in the `models`/`tasks`
      pair: `models.py:142` (`from .tasks import generate_thumbnail` inside
      `create_and_dispatch`), commented. `tasks.py` has zero lazy imports.
- [x] No duplicated timestamp-formatting code — `_fmt_ts(dt)` helper at
      `models.py:16` used by both `Image.__str__` and `ImageTask.__str__`.
- [x] `make test` green (37 passed); `make check` clean (ruff + ruff format +
      pyrefly).

## Readability guardrail

A `services.py` is only worth adding if it genuinely removes the import cycle and
reads better — not as ceremony. If a one-line comment on a single lazy import is
clearer than a new file, do that instead. Smallest change that removes the
"why is this here?" reaction.

## Open questions

- Are you open to an `images/services.py` layer, or do you want domain logic to
  stay on the models (fat-model style)? This decides how the circular import gets
  resolved. The project is small enough that either is reasonable — your call.
