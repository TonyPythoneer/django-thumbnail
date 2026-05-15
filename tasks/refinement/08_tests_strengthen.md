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

- [x] **Test the domain invariant.** `test_models.py::TestLatestTask` covers
      `test_latest_task_returns_newest`, `test_latest_task_none_when_no_tasks`,
      `test_current_status_reflects_newest_task`, `test_current_status_pending_when_no_tasks`,
      and `test_latest_task_uses_prefetch_cache` (locks in the task 05 prefetch).
- [x] **Add query-count tests** (supports task 05): `gallery` covered via
      `test_views_html.py::TestGallery::test_gallery_query_count_constant` (4 queries
      with 5 images + tasks). `images_list` covered via
      `test_api.py::TestImagesAPI::test_list_query_count_constant` (added this pass).
- [x] **Add HTML view tests.** `test_views_html.py` covers `TestGallery`
      (requires-login, own-images-only, query-count), `TestUpload` (GET form,
      POST creates Image), `TestHtmlLogin` (redirects authed user), and
      `TestImageDelete` (own image, owner-isolation).
- [x] **Test retry exhaustion.** `test_tasks.py::test_s3_error_marks_failed_after_exhausting_retries`
      asserts final status `FAILED` when retries exhaust; companion
      `test_s3_error_stays_processing_during_retry` asserts in-progress retry
      stays `PROCESSING`.
- [x] **De-duplicate the smoke test.** `test_smoke.py:134` now calls
      `Image.format_thumbnail_key_from_original(original_key)`.
- [x] **Decide on `test_image_upload.py`.** Deleted (commit `9ac9b94`) — third
      copy of a path already covered by `test_smoke.py` and the new HTML view tests.
- [x] **Tighten broad excepts.** `test_tasks.py:45,58` now use
      `pytest.raises(ConnectionError)` / `pytest.raises(Retry)` instead of
      `pytest.raises(Exception)`.
- [x] **Clarify the storage-isolation story.** Dead `STORAGES`/`InMemoryStorage`
      block removed from `settings/test.py` (commit `9ac9b94`); isolation now
      explicitly comes from `patch()` calls in each test module.
- [x] **Coverage:** task 09 dropped `pytest-cov` and decided against a coverage
      gate. Item resolved with no action required here.

## Acceptance

- [x] `latest_task()` / `current_status()` have direct tests proving "newest wins".
- [x] Every HTML view has at least one test; owner-isolation is asserted on the
      HTML delete path.
- [x] Retry exhaustion has a test.
- [x] No test re-implements logic that already exists as a model/helper method.
- [x] `make test` green (38 passed); `make smoke` green against `make up`
      *(runtime check deferred to task 10)*.

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
