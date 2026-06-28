from __future__ import annotations

import json
import time

from django.conf import settings
from django.http import StreamingHttpResponse
from ninja import Router

from apps.core.schemas import OkResponse
from apps.core.services.health import build_system_status
from system_profiler import collect_system_snapshot

router = Router(tags=["system"])


@router.get("/status", response=OkResponse)
def status(request):  # noqa: ANN001
    return {
        "ok": True,
        "data": build_system_status(settings),
        "meta": {},
    }


@router.get("/snapshot", response=OkResponse)
def snapshot(request):  # noqa: ANN001
    return {
        "ok": True,
        "data": collect_system_snapshot(),
        "meta": {},
    }


@router.get("/stream")
def stream(request):  # noqa: ANN001
    try:
        interval = max(1.0, float(request.GET.get("interval", "2")))
    except ValueError:
        interval = 2.0

    def event_stream():
        while True:
            payload = {
                "ok": True,
                "data": collect_system_snapshot(),
                "meta": {},
            }
            yield f"event: system-snapshot\ndata: {json.dumps(payload)}\n\n"
            time.sleep(interval)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
