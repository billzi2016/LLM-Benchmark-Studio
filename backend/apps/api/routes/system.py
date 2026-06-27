from __future__ import annotations

from django.conf import settings
from ninja import Router

from apps.core.schemas import OkResponse
from apps.core.services.health import build_system_status

router = Router(tags=["system"])


@router.get("/status", response=OkResponse)
def status(request):  # noqa: ANN001
    return {
        "ok": True,
        "data": build_system_status(settings),
        "meta": {},
    }
