from __future__ import annotations

from django.conf import settings
from ninja import Router

from apps.core.schemas import OkResponse
from apps.llms.registry import generation_models, load_model_registry

router = Router(tags=["models"])


@router.get("", response=OkResponse)
def list_models(request, include_inactive: bool = True, include_embedding: bool = False):  # noqa: ANN001
    models = load_model_registry(settings.LLM_MODEL_NAMES_PATH)
    if not include_embedding:
        models = generation_models(models)
    if not include_inactive:
        models = [model for model in models if model.get("activate")]
    return {"ok": True, "data": models, "meta": {"total": len(models)}}
