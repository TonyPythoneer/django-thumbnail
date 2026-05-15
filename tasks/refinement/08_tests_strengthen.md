# 08 — Strengthen the test suite

**Lens:** QA **Risk:** Low **Est. LOC delta:** +40 to +80 (tests are worth lines)

## Context

The existing suite (`test_api.py`, `test_tasks.py`, `test_task_utils.py`) is
decent for the JSON API and the task internals. But it has gaps — and the biggest
gap is the project's *headline feature*.

1. **The core domain invariant is untested.** The whole `Image` + `ImageTask`
   design is "a retry creates a new task row, full history, latest wins". No test
   creates two `ImageTask` rows for one `Image` and asserts `latest_task()` /
   `current_status()` returns the **newest**. The feature the README leads with
   has zero coverage.

2. **No HTML view tests at all.** `gallery`, `upload`, `html_login`,
   `html_logout`, `image_delete` (`views.py:131-200`) — five views, a 3-page UI,
   zero tests. Only the JSON API is covered.

3. **Retry-exhaustion path untested.** `test_s3_error_marks_failed`
   (`test_tasks.py:37-46`) confirms one failure marks `FAILED`, but with
   `CELERY_TASK_ALWAYS_EAGER` + `EAGER_PROPAGATES` the task retries up to
   `max_retries=3`. Nothing asserts what happens when retries are exhausted
   (`MaxRetriesExceededError`), nor the retry count.

4. **Smoke test re-implements a model method.** `test_smoke.py:135-143`
   reconstructs the thumbnail key by string-surgery on the URL
   (`rpartition(".")`, `f"{stem}_thumbnail{dot}{ext}"`) instead of calling
   `Image.format_thumbnail_key_from_original`. If the naming scheme changes, the
   smoke test silently rots.

5. **`test_image_upload.py` is a redundant third smoke mechanism.** The management
   command at `images/management/commands/test_image_upload.py` does a real-HTTP
   upload-and-dispatch — overlapping `test_smoke.py` and `make smoke`, wired into
   neither CI nor the Makefile. It also duplicates `ImageTask.create_and_dispatch`
   inline (`test_image_upload.py:59-62`).

6. **Over-broad exception assertions.** `test_tasks.py:43` uses
   `pytest.raises(Exception)` — catches anything, asserts nothing specific.

7. **`test.py` `InMemoryStorage` is inert.** `settings/test.py:14-17` configures
   `STORAGES` with `InMemoryStorage`, but the app never uses Django storages —
   isolation actually comes from the explicit `patch(...)` calls in the tests. Not
   a bug, but the README and the settings file imply a mechanism that does nothing.

## Checklist

- [ ] **Test the domain invariant.** New test: one `Image`, create 2–3 `ImageTask`
      rows in sequence, assert `latest_task()` and `current_status()` reflect the
      newest. This also locks in the **task 05** prefetch change — add a
      `django_assert_num_queries` variant for the prefetched path.
- [ ] **Add query-count tests** (supports task 05): assert `gallery` and
      `images_list` GET issue a constant number of queries as image count grows
      (`django_assert_num_queries`).
- [ ] **Add HTML view tests.** At minimum: `gallery` renders for an authed user and
      shows their images only; `upload` POST creates an `Image` + dispatches a task;
      `html_login` redirects authed users; `image_delete` is owner-scoped (a user
      cannot delete another user's image — mirror `test_delete_other_user_image`).
- [ ] **Test retry exhaustion.** Assert that after `max_retries` the task gives up
      cleanly and the final status is `FAILED` (and, if **task 06** adds
      `RETRYING`, that the status transitions are what you expect).
- [ ] **De-duplicate the smoke test.** `test_smoke.py` should call
      `Image.format_thumbnail_key_from_original` instead of reconstructing the key
      by string surgery.
- [ ] **Decide on `test_image_upload.py`.** Either delete it (CI + `test_smoke.py`
      already cover the path), or keep it and wire it into the `Makefile` with a
      clear purpose and make it reuse `create_and_dispatch`. Lean: delete.
- [ ] **Tighten broad excepts.** Replace `pytest.raises(Exception)` with the
      specific exception the code actually raises.
- [ ] **Clarify the storage-isolation story.** Either remove the inert
      `STORAGES`/`InMemoryStorage` block from `settings/test.py` (the `patch()`
      calls are doing the real work), or keep it and add a one-line comment that it
      is a safety net, not the mechanism. Hand the corrected wording to **task 01**
      so the README stops overstating it.
- [ ] **Coverage:** see **task 09** for whether a coverage threshold gets added —
      if it does, this task's new tests should clear it on the touched files.

## Acceptance

- [ ] `latest_task()` / `current_status()` have direct tests proving "newest wins".
- [ ] Every HTML view has at least one test; owner-isolation is asserted on the
      HTML delete path.
- [ ] Retry exhaustion has a test.
- [ ] No test re-implements logic that already exists as a model/helper method.
- [ ] `make test` green; `make smoke` green against `make up`.

## Readability guardrail

Tests are documentation. Name them for the behaviour they prove
(`test_current_status_reflects_newest_task`, not `test_status_2`). It is fine for
this task to *add* lines — a clear test earns its length. Keep the AAA
(arrange/act/assert) shape the existing tests already use.

## Open questions

- Keep or delete `test_image_upload.py`? (Lean: delete — it is a third copy of a
  flow already covered twice.)
- Is the HTML UI considered in-scope for the project's quality bar, or is the JSON
  API the "real" product? That sets how much HTML-view coverage is worth writing.
