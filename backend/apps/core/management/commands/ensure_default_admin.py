from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.admin_bootstrap import ensure_default_admin


class Command(BaseCommand):
    help = "Create or update the default Django admin user."

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        username = ensure_default_admin()
        self.stdout.write(self.style.SUCCESS(f"default admin ready: {username}"))

