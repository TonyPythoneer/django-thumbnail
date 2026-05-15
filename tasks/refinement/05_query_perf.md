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
- [ ] Change `Image.latest_task()` so that when `tasks` has been prefetched it
      reads from the cache instead of re-querying. Because `ImageTask.Meta.ordering`
      is `["-created_at"]`, the prefetched list is already sorted — the latest is
      simply the first element. A clean form:
      `next(iter(self.tasks.all()), None)` — `.all()` hits the prefetch cache;
      `.order_by(...)` would not.
- [ ] Verify: without a prefetch, `latest_task()` must still return the correct
      latest row (the `Meta.ordering` makes `self.tasks.all()` ordered even on a
      cold fetch — confirm with a test, see task 08).

### Fix the gallery query
- [ ] `gallery` (`views.py:158-178`): keep `prefetch_related("tasks")`, and ensure
      `latest_task()` now consumes it. After the fix, the gallery should be **2
      queries total** (images + their tasks), not 1 + N.
- [ ] Coordinate with **task 04**: the gallery row-dict construction is being moved
      into `models.py` there. The N+1 fix and the serializer move should land
      together so the gallery view ends up as a clean "fetch → serialize → render".

### Fix the JSON list API
- [ ] `images_list` GET (`views.py:42-43`): add `.prefetch_related("tasks")` to the
      queryset so `to_dict()` → `current_status()` → `latest_task()` reads from
      cache. After the fix this endpoint should be a small constant number of
      queries regardless of image count.
- [ ] **Consider** (optional, only if it reads cleanly): instead of prefetching
      whole task rows just to read one status, annotate the latest status onto the
      `Image` queryset with a `Subquery` / `OuterRef`. This is fewer rows fetched
      but more ORM machinery — only do it if the `Subquery` is genuinely readable.
      The prefetch fix above is the safe, obvious win; the annotation is a
      nice-to-have.

### Sanity-check other call sites
- [ ] `ImageTask.to_dict()` (`models.py:145-157`) touches `self.image.original_key`
      etc. `tasks_detail` already uses `select_related("image")` (`views.py:86`) —
      confirm that covers it. `tasks_create` builds a task then calls `to_dict()` —
      check it doesn't trigger an extra `image` fetch.

## Acceptance

- [ ] Add/extend tests in **task 08** that assert query counts with
      `django_assert_num_queries` (pytest-django) for `gallery` and
      `images_list` GET — they should be flat (constant) as image count grows.
- [ ] Manual check: load `/` with ~20 images, confirm via Django Debug Toolbar or
      query logging that it is ~2 queries, not ~20.
- [ ] `make test` green.

## Readability guardrail

`next(iter(self.tasks.all()), None)` is about as far as readability should bend —
it is a known Django idiom for "first of a prefetched relation". If the `Subquery`
annotation ends up dense or needs a comment to explain itself, **don't ship it** —
the prefetch fix alone solves the perf problem and stays obvious.

## Open questions

- Is the JSON `images_list` endpoint expected to handle large lists (pagination)?
  If lists can grow unbounded, note it — pagination is a separate, larger task,
  not in scope here, but worth flagging now.
