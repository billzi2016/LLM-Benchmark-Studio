from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from unittest.mock import patch

from apps.core.admin_bootstrap import ensure_default_admin


class AdminBootstrapTests(TestCase):
    @patch.dict(
        "os.environ",
        {
            "DJANGO_DEFAULT_ADMIN_USERNAME": "guest",
            "DJANGO_DEFAULT_ADMIN_PASSWORD": "guest",
            "DJANGO_DEFAULT_ADMIN_EMAIL": "guest@example.com",
        },
        clear=False,
    )
    def test_ensure_default_admin_creates_superuser(self) -> None:
        username = ensure_default_admin()
        user = get_user_model().objects.get(username=username)
        self.assertEqual(username, "guest")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("guest"))

    @patch.dict(
        "os.environ",
        {
            "DJANGO_DEFAULT_ADMIN_USERNAME": "guest",
            "DJANGO_DEFAULT_ADMIN_PASSWORD": "guest",
            "DJANGO_DEFAULT_ADMIN_EMAIL": "guest@example.com",
        },
        clear=False,
    )
    def test_ensure_default_admin_is_idempotent(self) -> None:
        ensure_default_admin()
        ensure_default_admin()
        self.assertEqual(get_user_model().objects.filter(username="guest").count(), 1)
