# 05 — Query performance: kill the N+1, fix the wasted prefetch

**Lens:** Solution Architect / QA **Risk:** Medium **Est. LOC delta:** −5 to +10

## Context

This is the main performance task. Two query problems, both around "what is the
latest task for this image".

1. **Straight N+1 in the JSON list API.** `images_list` GET does
   `[i.to_dict() for i in qs]` (`views.py:42-43`). `Image.to_dict()` calls
   `current_status()` → `latest_task()` → `self.tasks.order_by("-created_at").first()`
   (`models.py:44-49`). That is one extra query *per image*. 50 images = 51
   queries.

2. **Wasted prefetch in the gallery.** `gallery` does
   `Image.objects.for_user(request.user).prefetch_related("tasks")`
   (`views.py:159`) — good intention. But it then calls `img.latest_task()`, which
   does `self.tasks.order_by("-created_at").first()`. Calling `.order_by()` on a
   prefetched related manager **bypasses the prefetch cache and issues a fresh
   query**. So the gallery pays for the prefetch *and* still does N+1. `ImageTask`
   already has `Meta.ordering = ["-created_at"]`, so the prefetch cache is already
   newest-first — `latest_task()` just needs to read from it.

## Checklist

### Make `latest_task()` prefetch-aware
- [x] Change `Image.latest_task()` so that when `tasks` has been prefetched it
      reads from the cache instead of re-querying. Implemented as
      `next(iter(self.tasks.all()), None)` in `models.py:55`.
- [x] Verify: without a prefetch, `latest_task()` must still return the correct
      latest row — covered by `test_models.py` `latest_task` tests.

### Fix the gallery query
- [x] `gallery` (`views.py:163`): `prefetch_related("tasks")` kept; `latest_task()`
      consumes cache. `test_views_html.py` asserts constant query count.
- [x] Coordinate with **task 04**: `_gallery_row` serializer landed alongside the
      N+1 fix. View is "fetch → serialize → render".

### Fix the JSON list API
- [x] `images_list` GET (`views.py:39`): `.prefetch_related("tasks")` added.
- [x] **Consider** (optional) Subquery annotation — **skipped**, prefetch path
      is cleaner; annotation deferred as future work.

### Sanity-check other call sites
- [x] `ImageTask.to_dict()` call sites covered: `tasks_detail` uses
      `select_related("image")`; `tasks_create` already holds the image instance
      from the request flow — no extra fetch.

## Acceptance

- [x] Add/extend tests in **task 08** that assert query counts with
      `django_assert_num_queries` — landed in `test_views_html.py` + `test_models.py`.
- [~] Manual check: load `/` with ~20 images via Django Debug Toolbar (user-driven).
      *Skipped — covered by automated assertions in task 08:*
      `test_gallery_query_count_constant` (4 queries with 5 images + tasks),
      `test_list_query_count_constant` (same shape on the JSON API),
      `test_latest_task_uses_prefetch_cache`. Programmatic proof that query count
      stays flat as image count grows beats a one-off visual check.
- [x] `make test` green.

## Readability guardrail

`next(iter(self.tasks.all()), None)` is about as far as readability should bend —
it is a known Django idiom for "first of a prefetched relation". If the `Subquery`
annotation ends up dense or needs a comment to explain itself, **don't ship it** —
the prefetch fix alone solves the perf problem and stays obvious.

## Open questions

- Is the JSON `images_list` endpoint expected to handle large lists (pagination)?
  If lists can grow unbounded, note it — pagination is a separate, larger task,
  not in scope here, but worth flagging now.
