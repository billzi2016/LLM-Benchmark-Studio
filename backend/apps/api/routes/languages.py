from __future__ import annotations

from django.conf import settings
from ninja import Router

from apps.core.schemas import OkResponse
from apps.datasets.languages import load_languages

router = Router(tags=["languages"])


@router.get("", response=OkResponse)
def list_languages(request, include_inactive: bool = True):  # noqa: ANN001
    languages = load_languages(settings.LANGUAGES_PATH)
    if not include_inactive:
        languages = [language for language in languages if language.get("activate")]
    return {"ok": True, "data": languages, "meta": {"total": len(languages)}}
