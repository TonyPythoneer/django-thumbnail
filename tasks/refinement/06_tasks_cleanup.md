# 06 — Clean up the Celery task

**Lens:** Solution Architect / QA **Risk:** Medium **Est. LOC delta:** −15 to −25

## Context

`images/tasks.py` (91 lines) is the heart of the project, and it has accumulated
a few issues — one of them probably a bug.

1. **`THUMBNAIL_SIZE = (20, 20)` (`tasks.py:16`).** `CLAUDE.md` describes a
   "300×300 thumbnail"; the README sells "real thumbnails". 20×20 px is almost
   certainly a leftover debug value. A reviewer of a "thumbnail worker" that emits
   20px images will notice immediately. `test_task_utils.py:30-35` just asserts the
   output equals `THUMBNAIL_SIZE`, so it follows whatever the constant says — the
   test won't catch the wrong value.

2. **The image is opened twice.** `_process_thumbnail` (`tasks.py:29-33`) calls
   `_validate_image_buffer` (opens + `verify()` + seeks back) then
   `_create_thumbnail_buffer` (opens again). PIL's `verify()` does invalidate the
   object so a reopen is required *if* you keep them separate — but validate and
   thumbnail can be done in a single open with a `try/except` for the
   invalid-image case.

3. **OTel plumbing is mixed into domain logic.** `tasks.py:84-91` — the `finally`
   block reaches into `trace.get_tracer_provider()`, type-checks it, and calls
   `force_flush()`. That is ~8 lines of telemetry mechanics inside what should read
   as "process the image, record the outcome".

4. **Stale telemetry comment / processor mismatch.** The comment at `tasks.py:87-88`
   says "Celery prefork workers don't inherit the **BSP** exporter thread after
   fork" — BSP = `BatchSpanProcessor`. But `telemetry.py` uses
   `SimpleSpanProcessor`, which exports synchronously on `span.end()`. With
   `SimpleSpanProcessor` the `force_flush()` is essentially redundant. Either the
   comment is stale, or the processor choice is. (README also claims a dev/prod
   processor switch that does not exist — see task 01.)

5. **Retry status semantics.** The `except Exception` branch (`tasks.py:79-83`)
   does `task.mark_failed(...)` *then* `raise self.retry(...)`. So while a task is
   mid-retry its status is `FAILED`, not "processing" or "retrying" — a user
   polling sees `failed`, then it may flip to `done`. There is an `Outcome.RETRY`
   enum value but no `ImageStatus.RETRYING`. This may be an intentional
   simplification; flag it for a decision.

## Checklist

- [ ] **Fix `THUMBNAIL_SIZE`.** Confirm the intended size (CLAUDE.md says 300×300)
      and set it. Update `test_task_utils.py` expectations if needed (it should
      still assert "output respects `THUMBNAIL_SIZE`", just with the right value).
- [ ] **Single open.** Merge validation into the thumbnail path: open once, catch
      PIL's decode error to raise `InvalidImageError`, thumbnail in the same block.
      Keep `_validate_image_buffer` only if a test still needs it as a unit (see
      task 08) — otherwise inline and delete.
- [x] **Extract the flush.** Dropped entirely — `SimpleSpanProcessor` exports
      synchronously on `span.end()`; `force_flush()` was a no-op. Stale BSP
      comment removed. `TracerProvider` import removed from `tasks.py`.
- [x] **Resolve the BSP/Simple mismatch.** Keep `SimpleSpanProcessor`. Removed
      `force_flush()` and stale BSP comment. README claim dropped. Decision handed
      to **task 01**.
- [x] **Span attributes.** `span.set_attributes(dict)` kept; no regression.
- [x] **Decide on retry status.** Adopted Opus suggestion: status stays
      `PROCESSING` during retries; `mark_failed()` only called when
      `retries >= max_retries`. Added `Outcome.FAIL` for terminal-failure spans.
      Test updated to simulate exhausted retries via `apply(retries=max_retries)`.

## Acceptance

- [ ] Thumbnails come out at the intended size — verified by a test and by an
      eyeball check of a real upload via `make smoke` / the UI.
- [ ] The happy path opens the image once.
- [ ] `tasks.py` reads as domain logic; no `TracerProvider` `isinstance` check in it.
- [ ] Code, comments, and docs agree on which span processor is used and why.
- [ ] `make test` green.

## Readability guardrail

The `generate_thumbnail` body should read like a story: get the task, mark it
processing, try to produce the thumbnail, record the outcome. Telemetry is a
*detail* — push it behind named helpers, don't let it dominate the function.

## Open questions

- **`THUMBNAIL_SIZE` — what is the intended value?** 300×300 per `CLAUDE.md`?
  Confirm before changing; this is the one item here that changes user-visible
  output.
- Do you want a real `RETRYING` status, or is "FAILED, may recover" acceptable for
  a side project? This decides whether a migration is in scope.
