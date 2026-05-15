# Project Refinement Plan — Overview & Index

## Goal

Refine the whole project for **performance** and **fewer lines of code**, without
hurting **readability**. Readability is the priority: every change must make the
code easier to engage with and review, not harder.

This plan was produced by reviewing the codebase through three lenses:

- **CTO** — risk, consistency, "does the project hang together", credibility.
- **Solution Architect** — design, layering, naming, abstractions, duplication.
- **QA** — tests, correctness, edge cases, CI gates.

The project is small (~1,100 lines of Python). Nothing here is a rewrite — these
are surgical, low-risk improvements.

---

## Outcome (2026-05-16)

All tasks 01–09 closed (see each `NN_*.md` for details). Task 10 covers final
verification; runtime/docker checks deferred to user.

**LOC delta vs merge-base `d6ac5ce` (start of `refactor/simply`):**

| Slice | base | head | Δ |
|---|---|---|---|
| Production code (excl `migrations/`, `tests/`) | 1,595 | 1,523 | **−72 (−4.5%)** |
| Test code | 514 | 651 | **+137** *(task 08, expected)* |
| All Python (excl `migrations/`) | 2,109 | 2,174 | +65 |

The −4.5% on production code is below the original ~15% aspiration. Reason:
several wins were *clarity-positive but line-neutral* (e.g. task 06's single-PIL-
open refactor) and a couple of deliberate additions paid for themselves —
`django_thumbnail/apps.py` (+23, project-level OTel init via `CoreConfig`) and
`images/decorators.py` (+21, `login_required_json` deduplication). Test suite
grew on purpose to close the headline-feature coverage gap.

Deferred / skipped (intentional, with rationale in the respective task files):

- **05** Debug Toolbar manual check — superseded by automated
  `django_assert_num_queries` tests added in task 08.
- **03** S3 client construction at import time — accepted as-is; no test impact.
- **10** runtime gates (`make up`, `make smoke`, Jaeger browser check, fresh-clone
  Quick Start) — user-driven; cannot be exercised without spinning up the docker
  stack.

---

## Findings summary

| # | Task file | Lens | Risk | Why it matters |
|---|---|---|---|---|
| 01 | `01_docs_drift_fix.md` | CTO | Low | README/CLAUDE.md/OBSERVABILITY.md describe a project that no longer exists — broken `make` commands, wrong layout, fictional `apps.py` wiring. The front door lies. |
| 02 | `02_settings_and_entrypoints.md` | CTO / SA | Low | Empty `settings/__init__.py` + `setdefault` points there → bare `manage.py` crashes. Telemetry init lives in `manage.py` (runs for *every* command); `wsgi.py`/`asgi.py` never init it. |
| 03 | `03_storage_module.md` | SA | Medium | `utils.py` is a junk drawer (S3 clients + an auth decorator). S3 client construction duplicated in 2 management commands. Clients built at import time. |
| 04 | `04_views_slim.md` | SA | Low | JSON-body parsing copy-pasted 3×. `gallery` view hand-builds a dict that overlaps `Image.to_dict()` — two serializers for one model. |
| 05 | `05_query_perf.md` | SA / QA | Medium | `images_list` has a real N+1. `gallery` calls `prefetch_related("tasks")` but `latest_task()` bypasses the cache — the prefetch is wasted. |
| 06 | `06_tasks_cleanup.md` | SA / QA | Medium | `THUMBNAIL_SIZE = (20, 20)` looks like a leftover debug value. Image opened twice. OTel flush logic mixed into domain code; its comment references `BatchSpanProcessor` but the code uses `SimpleSpanProcessor`. |
| 07 | `07_models_cleanup.md` | SA | Low | Dead `django-storages` settings. Circular import worked around with two lazy imports. Duplicated `__str__` timestamp logic. |
| 08 | `08_tests_strengthen.md` | QA | Low | The headline domain invariant (`latest_task` / retry history) is untested. No HTML view tests. Retry-exhaustion path untested. Smoke test re-implements a model method. |
| 09 | `09_tooling_ci.md` | CTO / QA | Low | No `[tool.ruff]` config. CI runs `ruff check` but not `ruff format --check` or `pyright`. `pytest-cov` installed but no coverage gate. |
| 10 | `10_verification.md` | QA | — | Final gate: run the suite, follow the README literally, measure the LOC delta, self-review for readability regressions. |

---

## Suggested execution order & dependencies

```
01  docs            ── independent, do first (forces a full re-read of reality)
02  settings        ── foundational, low risk
03  storage module  ── refactor; views/models import from it → do before 04 & 05
        │
        ├── 04  views slim      (needs the helper location from 03)
        └── 05  query perf      (can run alongside 04)
06  tasks cleanup    ── mostly independent
07  models cleanup   ── touches models.py; sequence after 05 (also touches models)
08  tests strengthen ── adjust tests alongside 03–07; this file is the consolidated pass
09  tooling / CI     ── do the [tool.ruff] part early (guides everything else)
10  verification     ── last
```

Tasks 04 and 05 can be done in parallel. Everything else is best done in order.

---

## Global guardrails (apply to every task)

- **Readability beats brevity.** If shortening code makes it cleverer or denser,
  stop — keep the longer, obvious version. A helper must have a name that explains
  itself.
- **No new abstractions "for later."** Only extract a helper when the duplication
  already exists (it does, in several places).
- **Run `make test` and `make lint` after each task.** Keep the suite green the
  whole way through.
- **No auto-commit.** Show the diff, wait for explicit approval before committing.
- **One task = one reviewable change.** Each numbered file is sized to be a single
  commit / PR so review stays easy.
- **Update the relevant docs in the same task** (or note it for task 01) — don't
  let drift creep back in.

---

## How to use these files

Each `NN_*.md` file is a **checklist**. Work top to bottom:

1. Read the **Context** so the change makes sense.
2. Tick the **Checklist** items as you go (`- [ ]` → `- [x]`).
3. Confirm the **Acceptance** criteria before marking the task done.
4. Respect the **Readability guardrail** in every file.

Open questions are flagged inside each file — answer those before touching code.

> Folder named `tasks/refinement/` — rename if you prefer another label.
