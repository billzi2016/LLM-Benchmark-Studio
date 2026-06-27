from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.datasets.catalog import scan_datasets
from apps.datasets.languages import load_languages
from apps.llms.registry import load_model_registry


def file_status(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
    }


def build_system_status(settings: Any) -> dict[str, Any]:
    models = load_model_registry(settings.LLM_MODEL_NAMES_PATH)
    languages = load_languages(settings.LANGUAGES_PATH)
    datasets = scan_datasets(settings.BENCHMARK_DATASETS_DIR)
    return {
        "service": "django",
        "status": "ok",
        "data_dir": str(settings.DATA_DIR),
        "benchmark_datasets_dir": str(settings.BENCHMARK_DATASETS_DIR),
        "files": {
            "llm_model_names": file_status(settings.LLM_MODEL_NAMES_PATH),
            "languages": file_status(settings.LANGUAGES_PATH),
        },
        "providers": {
            "default_provider": settings.DEFAULT_PROVIDER,
            "judge_provider": settings.JUDGE_PROVIDER,
            "judge_model": settings.JUDGE_MODEL,
            "translate_provider": settings.TRANSLATE_PROVIDER,
            "translate_model": settings.TRANSLATE_MODEL,
            "available": [
                {
                    "provider": config["provider"],
                    "protocol": config["protocol"],
                    "base_url": config["base_url"],
                    "enabled": config["enabled"],
                    "api_key_configured": bool(config.get("api_key")),
                }
                for config in settings.LLM_PROVIDERS.values()
            ],
        },
        "contexts": {
            "think": settings.LLM_CONTEXT_THINK,
            "no_think": settings.LLM_CONTEXT_NO_THINK,
        },
        "counts": {
            "models_total": len(models),
            "models_active": sum(1 for model in models if model.get("activate")),
            "languages_total": len(languages),
            "languages_active": sum(1 for language in languages if language.get("activate")),
            "datasets_total": len(datasets),
            "datasets_active": sum(1 for dataset in datasets if dataset.get("activate")),
        },
        "dependencies": {
            "postgresql": {
                "host": settings.DATABASES["default"].get("HOST", "sqlite"),
                "configured": settings.DATABASES["default"]["ENGINE"].endswith("postgresql"),
            },
            "rabbitmq": {
                "host": settings.RABBITMQ_HOST,
                "port": settings.RABBITMQ_PORT,
                "configured": bool(settings.CELERY_BROKER_URL),
            },
            "ollama": {
                "base_url": settings.OLLAMA_BASE_URL,
            },
        },
    }
