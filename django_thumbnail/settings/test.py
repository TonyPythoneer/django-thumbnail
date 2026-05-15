from .base import *  # noqa: F401, F403

# ── Django core ──────────────────────────────────────────────
DEBUG = True

# ── OpenTelemetry ─────────────────────────────────────────────
OTEL_SDK_DISABLED = True

# ── Celery ───────────────────────────────────────────────────
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
