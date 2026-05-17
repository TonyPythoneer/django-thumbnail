"""Permanent test accounts shared by dev/test settings.

Imported explicitly by local.py / test.py. Prod settings must NOT
import this — base.py leaves TEST_USERS empty so create_test_users
no-ops on prod.
"""

TEST_USERS: list[tuple[str, str]] = [
    ("test1@example.com", "test1"),
    ("test2@example.com", "test2"),
]
