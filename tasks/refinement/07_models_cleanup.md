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
- [ ] Delete `AWS_S3_ADDRESSING_STYLE`, `AWS_DEFAULT_ACL`, `AWS_QUERYSTRING_AUTH`
      from `settings/base.py` — confirm via grep that nothing reads them first.
- [ ] While in `base.py`: scan for any other settings that no longer have a
      consumer (the file is 122 lines; a quick audit is cheap).

### Circular import
- [ ] Untangle the `models` ↔ `tasks` cycle so the lazy imports can go away, or at
      least so there is only one. Cleanest option: move the "create an `ImageTask`
      row and dispatch the Celery job" step out of the model into a thin
      `images/services.py` (or into the view layer) — then `tasks.py` imports
      `models`, the service imports both, and nothing imports backwards.
- [ ] If you keep `create_and_dispatch` on the model, leave a one-line comment
      explaining the cycle (the existing comment at `models.py:135-137` is fine —
      just make sure only *one* lazy import remains, not two).

### `__str__` dedup
- [ ] Factor the timestamp formatting once. A module-level
      `_fmt_ts(dt) -> str` helper, or accept plain `str(self.created_at)` if the
      exact format does not matter for admin display. Don't over-think this — it is
      ~4 duplicated lines.

### Serialization home
- [ ] After **task 04** lands, confirm: is there exactly one discoverable place
      that serializes `Image`? If `to_dict()` stays on the model, the gallery must
      use it (or a sibling method on the model) — no anonymous inline dict.

## Acceptance

- [ ] `grep -r AWS_S3_ADDRESSING_STYLE` (and the other two) returns only the
      deletion — nothing consumed them.
- [ ] At most one lazy/deferred import remains in the `models`/`tasks` pair, and it
      is commented, or the cycle is gone entirely.
- [ ] No duplicated timestamp-formatting code.
- [ ] `make test` and `make lint` green.

## Readability guardrail

A `services.py` is only worth adding if it genuinely removes the import cycle and
reads better — not as ceremony. If a one-line comment on a single lazy import is
clearer than a new file, do that instead. Smallest change that removes the
"why is this here?" reaction.

## Open questions

- Are you open to an `images/services.py` layer, or do you want domain logic to
  stay on the models (fat-model style)? This decides how the circular import gets
  resolved. The project is small enough that either is reasonable — your call.
