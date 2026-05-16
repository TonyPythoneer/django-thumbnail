from .base import *  # noqa: F401, F403

# ── Django core ──────────────────────────────────────────────
DEBUG = True

ALLOWED_HOSTS = ["*"]

# ── OpenTelemetry ─────────────────────────────────────────────
OTEL_SDK_DISABLED = False

# ── Test accounts ────────────────────────────────────────────
from ._test_users import TEST_USERS  # noqa: E402, F401
