from __future__ import annotations

from django.conf import settings
from ninja import Router, Schema

from apps.core.schemas import OkResponse
from apps.llms.ollama import OllamaClient
from apps.llms.providers import get_provider, sanitize_provider_configs

router = Router(tags=["llms"])


class GenerateRequest(Schema):
    model: str
    prompt: str
    temperature: float = 0.0
    max_tokens: int = 128


@router.get("/providers", response=OkResponse)
def list_providers(request):  # noqa: ANN001
    return {
        "ok": True,
        "data": sanitize_provider_configs(settings.LLM_PROVIDERS),
        "meta": {"default_provider": settings.DEFAULT_PROVIDER},
    }


@router.get("/{provider_name}/health", response=OkResponse)
def provider_health(request, provider_name: str):  # noqa: ANN001
    provider = get_provider(provider_name, settings.LLM_PROVIDERS)
    return {"ok": True, "data": provider.health(), "meta": {}}


@router.post("/{provider_name}/generate", response=OkResponse)
def provider_generate(request, provider_name: str, payload: GenerateRequest):  # noqa: ANN001
    provider = get_provider(provider_name, settings.LLM_PROVIDERS)
    response = provider.generate(
        model=payload.model,
        prompt=payload.prompt,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )
    return {"ok": True, "data": response, "meta": {}}


@router.get("/ollama/health", response=OkResponse)
def ollama_health(request):  # noqa: ANN001
    client = OllamaClient(settings.OLLAMA_BASE_URL, timeout=settings.OLLAMA_TIMEOUT_SECONDS)
    return {"ok": True, "data": client.health(), "meta": {}}


@router.post("/ollama/generate", response=OkResponse)
def ollama_generate(request, payload: GenerateRequest):  # noqa: ANN001
    client = OllamaClient(settings.OLLAMA_BASE_URL, timeout=settings.OLLAMA_TIMEOUT_SECONDS)
    response = client.generate(
        model=payload.model,
        prompt=payload.prompt,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )
    return {"ok": True, "data": response, "meta": {}}
