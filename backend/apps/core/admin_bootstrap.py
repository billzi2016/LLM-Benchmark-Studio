from __future__ import annotations

import os

from django.contrib.auth import get_user_model


def ensure_default_admin() -> str:
    username = os.getenv("DJANGO_DEFAULT_ADMIN_USERNAME", "guest")
    password = os.getenv("DJANGO_DEFAULT_ADMIN_PASSWORD", "guest")
    email = os.getenv("DJANGO_DEFAULT_ADMIN_EMAIL", "guest@example.com")

    user_model = get_user_model()
    user, created = user_model.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    updated = False
    if user.email != email:
        user.email = email
        updated = True
    if not user.is_staff:
        user.is_staff = True
        updated = True
    if not user.is_superuser:
        user.is_superuser = True
        updated = True
    user.set_password(password)
    updated = True
    if created or updated:
        user.save()
    return username

