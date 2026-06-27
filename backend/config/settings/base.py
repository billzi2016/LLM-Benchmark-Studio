from __future__ import annotations

import importlib.util
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BASE_DIR.parent
DATA_DIR = REPO_ROOT / "data"
BENCHMARK_DATASETS_DIR = DATA_DIR / "benchmark_datasets"
LLM_MODEL_NAMES_PATH = DATA_DIR / "llm_model_names.json"
LANGUAGES_PATH = DATA_DIR / "languages.json"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-development-secret-key")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "0.0.0.0"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

if importlib.util.find_spec("corsheaders"):
    INSTALLED_APPS.append("corsheaders")

if importlib.util.find_spec("django_celery_results"):
    INSTALLED_APPS.append("django_celery_results")

INSTALLED_APPS.extend(
    [
        "apps.core",
        "apps.datasets",
        "apps.llms",
        "apps.api",
    ]
)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
]

if importlib.util.find_spec("corsheaders"):
    MIDDLEWARE.append("corsheaders.middleware.CorsMiddleware")

MIDDLEWARE.extend(
    [
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]
)

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DJANGO_DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DJANGO_SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}

if os.getenv("DATABASE_URL") or os.getenv("POSTGRES_HOST"):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "llm_benchmark_studio"),
        "USER": os.getenv("POSTGRES_USER", "llm_benchmark"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "change_me"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", ["http://localhost:5173"])
CORS_ALLOWED_ORIGINS = env_list("FRONTEND_ALLOWED_ORIGINS", ["http://localhost:5173"])
CORS_ALLOW_CREDENTIALS = True

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "same-origin"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30"))

DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "ollama")
JUDGE_PROVIDER = os.getenv("JUDGE_PROVIDER", "ollama")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-oss:20b")
TRANSLATE_PROVIDER = os.getenv("TRANSLATE_PROVIDER", "ollama")
TRANSLATE_MODEL = os.getenv("TRANSLATE_MODEL", "gpt-oss:20b")
LLM_CONTEXT_THINK = int(os.getenv("LLM_CONTEXT_THINK", "65536"))
LLM_CONTEXT_NO_THINK = int(os.getenv("LLM_CONTEXT_NO_THINK", "16384"))
LLM_PROVIDER_TIMEOUT_SECONDS = float(os.getenv("LLM_PROVIDER_TIMEOUT_SECONDS", "120"))

LLM_PROVIDERS = {
    "ollama": {
        "provider": "ollama",
        "protocol": "ollama",
        "base_url": OLLAMA_BASE_URL,
        "api_key": "",
        "timeout": OLLAMA_TIMEOUT_SECONDS,
        "enabled": env_bool("OLLAMA_ENABLED", True),
    },
    "openai": {
        "provider": "openai",
        "protocol": "openai_compatible",
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "timeout": LLM_PROVIDER_TIMEOUT_SECONDS,
        "enabled": env_bool("OPENAI_ENABLED", False),
    },
    "openrouter": {
        "provider": "openrouter",
        "protocol": "openai_compatible",
        "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "timeout": LLM_PROVIDER_TIMEOUT_SECONDS,
        "enabled": env_bool("OPENROUTER_ENABLED", False),
    },
    "vllm": {
        "provider": "vllm",
        "protocol": "openai_compatible",
        "base_url": os.getenv(
            "VLLM_BASE_URL",
            f"http://{os.getenv('VLLM_HOST', 'localhost')}:{os.getenv('VLLM_PORT', '8000')}/v1",
        ),
        "api_key": os.getenv("VLLM_API_KEY", ""),
        "timeout": LLM_PROVIDER_TIMEOUT_SECONDS,
        "enabled": env_bool("VLLM_ENABLED", False),
    },
    "sglang": {
        "provider": "sglang",
        "protocol": "openai_compatible",
        "base_url": os.getenv(
            "SGLANG_BASE_URL",
            f"http://{os.getenv('SGLANG_HOST', 'localhost')}:{os.getenv('SGLANG_PORT', '30000')}/v1",
        ),
        "api_key": os.getenv("SGLANG_API_KEY", ""),
        "timeout": LLM_PROVIDER_TIMEOUT_SECONDS,
        "enabled": env_bool("SGLANG_ENABLED", False),
    },
    "openai_compatible": {
        "provider": "openai_compatible",
        "protocol": "openai_compatible",
        "base_url": os.getenv(
            "OPENAI_COMPATIBLE_BASE_URL",
            f"http://{os.getenv('OPENAI_COMPATIBLE_HOST', 'localhost')}:{os.getenv('OPENAI_COMPATIBLE_PORT', '6328')}/v1",
        ),
        "api_key": os.getenv("OPENAI_COMPATIBLE_API_KEY", ""),
        "timeout": LLM_PROVIDER_TIMEOUT_SECONDS,
        "enabled": env_bool("OPENAI_COMPATIBLE_ENABLED", False),
    },
}

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "django-db")
CELERY_TASK_DEFAULT_QUEUE = os.getenv("CELERY_TASK_DEFAULT_QUEUE", "llm_benchmark.serial")
CELERY_WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", "1"))
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))
CELERY_TASK_ACKS_LATE = env_bool("CELERY_TASK_ACKS_LATE", True)
