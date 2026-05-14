from .base import *  # noqa: F401, F403

# ── Django core ──────────────────────────────────────────────
DEBUG = True

ALLOWED_HOSTS = ["*"]

# ── OpenTelemetry ─────────────────────────────────────────────
OTEL_SDK_DISABLED = False
