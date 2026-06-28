from __future__ import annotations

from pathlib import Path
import socket
from typing import Any

from config.celery import app as celery_app
from apps.datasets.catalog import scan_datasets
from apps.datasets.languages import load_languages
from apps.llms.providers import get_provider
from apps.llms.registry import generation_models, load_model_registry
from django.db import connection


def file_status(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
    }


def ok_service(name: str, label: str, detail: str = "") -> dict[str, Any]:
    return {"name": name, "label": label, "status": "ok", "detail": detail}


def error_service(name: str, label: str, exc: Exception) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "status": "error",
        "detail": f"{exc.__class__.__name__}: {exc}",
    }


def disabled_service(name: str, label: str, detail: str = "disabled") -> dict[str, Any]:
    return {"name": name, "label": label, "status": "off", "detail": detail}


def check_database() -> dict[str, Any]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # noqa: BLE001
        return error_service("postgresql", "PostgreSQL", exc)
    db = connection.settings_dict
    return ok_service("postgresql", "PostgreSQL", f"{db.get('HOST')}:{db.get('PORT')}")


def check_tcp(name: str, label: str, host: str, port: int) -> dict[str, Any]:
    try:
        with socket.create_connection((host, int(port)), timeout=2):
            pass
    except Exception as exc:  # noqa: BLE001
        return error_service(name, label, exc)
    return ok_service(name, label, f"{host}:{port}")


def build_provider_statuses(settings: Any) -> list[dict[str, Any]]:
    providers: list[dict[str, Any]] = []
    for provider_name, config in sorted(settings.LLM_PROVIDERS.items()):
        detail = str(config.get("base_url") or "")
        if not config.get("enabled"):
            providers.append(
                {
                    "provider": config["provider"],
                    "protocol": config["protocol"],
                    "base_url": config["base_url"],
                    "enabled": config["enabled"],
                    "api_key_configured": bool(config.get("api_key")),
                    "status": "off",
                    "detail": "disabled",
                    "model_count": None,
                }
            )
            continue
        try:
            health = get_provider(provider_name, settings.LLM_PROVIDERS).health()
        except Exception as exc:  # noqa: BLE001
            providers.append(
                {
                    "provider": config["provider"],
                    "protocol": config["protocol"],
                    "base_url": config["base_url"],
                    "enabled": config["enabled"],
                    "api_key_configured": bool(config.get("api_key")),
                    "status": "error",
                    "detail": f"{exc.__class__.__name__}: {exc}",
                    "model_count": None,
                }
            )
            continue
        model_count = health.get("model_count")
        if model_count is not None:
            detail = f"{detail} · {model_count} models"
        providers.append(
            {
                "provider": config["provider"],
                "protocol": config["protocol"],
                "base_url": config["base_url"],
                "enabled": config["enabled"],
                "api_key_configured": bool(config.get("api_key")),
                "status": "ok",
                "detail": detail,
                "model_count": model_count,
            }
        )
    return providers


def check_celery_worker() -> dict[str, Any]:
    try:
        inspect = celery_app.control.inspect(timeout=1)
        response = inspect.ping() or {}
    except Exception as exc:  # noqa: BLE001
        return error_service("celery", "Celery Worker", exc)
    if not response:
        return disabled_service("celery", "Celery Worker", "no worker reply")
    return ok_service("celery", "Celery Worker", ", ".join(sorted(response.keys())))


def build_system_status(settings: Any) -> dict[str, Any]:
    models = generation_models(load_model_registry(settings.LLM_MODEL_NAMES_PATH))
    languages = load_languages(settings.LANGUAGES_PATH)
    datasets = scan_datasets(settings.BENCHMARK_DATASETS_DIR)
    provider_statuses = build_provider_statuses(settings)
    services = [
        ok_service("backend", "Django API", "running"),
        check_database(),
        check_tcp("rabbitmq", "RabbitMQ", settings.RABBITMQ_HOST, settings.RABBITMQ_PORT),
        check_celery_worker(),
    ]
    return {
        "service": "django",
        "status": "ok" if all(service["status"] != "error" for service in services) else "error",
        "services": services,
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
                    **provider,
                }
                for provider in provider_statuses
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
