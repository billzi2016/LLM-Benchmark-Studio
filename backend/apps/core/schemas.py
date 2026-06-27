from __future__ import annotations

from typing import Any

from ninja import Schema


class ApiError(Schema):
    code: str
    message: str
    details: dict[str, Any] = {}


class OkResponse(Schema):
    ok: bool
    data: Any
    meta: dict[str, Any] = {}
