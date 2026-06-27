from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_model_registry(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("llm_model_names.json must be a list.")
    return data


def is_generation_model(model: dict[str, Any]) -> bool:
    metadata = model.get("metadata") or {}
    model_type = str(metadata.get("type") or "generation").lower()
    model_role = str(metadata.get("role") or "").lower()
    modality = str(metadata.get("modality") or "text").lower()
    name = str(model.get("name") or "").lower()
    family = str(model.get("family") or "").lower()
    blocked_types = {"embedding", "translation", "rerank", "reranker", "classifier"}
    blocked_roles = {"translation"}
    blocked_modalities = {"vision", "ocr", "audio", "image"}
    blocked_terms = ("embed", "translate", "coder", "vision", "ocr", "rerank")
    return (
        model_type not in blocked_types
        and model_role not in blocked_roles
        and modality not in blocked_modalities
        and not any(term in name or term in family for term in blocked_terms)
    )


def generation_models(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [model for model in models if is_generation_model(model)]
