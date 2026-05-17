from .base import *  # noqa: F401, F403

# ── Django core ──────────────────────────────────────────────
DEBUG = True

# ── OpenTelemetry ─────────────────────────────────────────────
OTEL_SDK_DISABLED = True

# ── Celery ───────────────────────────────────────────────────
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ── Test accounts ────────────────────────────────────────────
from ._test_users import TEST_USERS  # noqa: E402, F401
