# 10 — Final verification

**Lens:** QA **Risk:** — **Est. LOC delta:** 0

## Context

The closing gate. After tasks 01–09, prove the refinement actually achieved its
three goals — **better performance, fewer lines, no readability regression** — and
that nothing broke on the way. Do this as one deliberate pass, not piecemeal.

## Checklist

### The suite & gates
- [ ] `make test` — green.
- [ ] `make lint` — clean.
- [ ] `ruff format --check` — clean (no drift).
- [ ] Type check (`pyright` / `ty`, per task 09) — clean.
- [ ] `make ci` (the new full-gate target from task 09) — green.
- [ ] `make up` then `make smoke` — green against the real docker-compose stack.

### Behaviour still works (manual)
- [ ] `make up`, open `http://localhost:8000`, log in as `test1@example.com`.
- [ ] Upload an image → it appears in the gallery → status moves
      `pending → processing → done` → a thumbnail renders.
- [ ] Confirm the thumbnail is the **intended size** (task 06) — not 20px.
- [ ] Delete an image → it disappears and is gone from storage.
- [ ] Open Jaeger (`http://localhost:16686`) → one trace spans app + worker + S3
      with correct parent/child nesting (the project's headline feature still
      works after the task 02 telemetry-init move).

### Goal: performance
- [ ] Re-check the queries: `gallery` and `images_list` GET are flat (constant
      query count) regardless of image count — the task 05 fix holds. Verify with
      the `django_assert_num_queries` tests from task 08, or query logging.
- [ ] Confirm importing `images.models` no longer constructs a boto3 client at
      import time (task 03).

### Goal: fewer lines
- [ ] Measure the Python LOC delta against the start of `refactor/simply`:
      `git diff --stat feat/setup` (or whatever the base is). Record the before/after
      numbers in `00_overview.md`. Target was a meaningful reduction (~15%); if it
      came in lower, that's fine *if* readability went up — note why.
- [ ] No file got *longer* without a good reason (tests in task 08 are the allowed
      exception).

### Goal: readability (the real one)
- [ ] Re-read `views.py`, `tasks.py`, `models.py`, `storage.py` cold. Each function
      should read top-to-bottom as a small story. If any change made code *cleverer*
      rather than *clearer*, revert that part — brevity was never the point.
- [ ] No new helper exists without an obvious, self-explaining name.
- [ ] Follow the README Quick Start **literally** on a fresh clone — every command
      works, every path resolves (closes the loop on task 01).
- [ ] `CLAUDE.md` §0 reflects reality: branch, current state, and a pointer to this
      plan's outcome.

### Close out
- [ ] Tick every box in `01`–`09`. Any item deliberately skipped → note why in
      `00_overview.md`.
- [ ] Update `00_overview.md` with the final LOC numbers and a one-line outcome
      summary.
- [ ] Confirm the working tree is in reviewable shape — coherent commits, one
      logical change each (per the global guardrail). **Do not commit without
      explicit approval.**

## Acceptance

- [ ] All gates green; the app works end-to-end including distributed tracing.
- [ ] Performance goals verified, not assumed.
- [ ] LOC delta measured and recorded.
- [ ] A cold re-read confirms the code is easier to engage with than before — that
      is the bar this whole plan was held to.

## Readability guardrail

This task *is* the readability guardrail. If the honest answer to "is this easier
to review now?" is no for any file, the refinement isn't done for that file —
go back, don't rationalise.
