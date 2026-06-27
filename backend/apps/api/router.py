from __future__ import annotations

from ninja import NinjaAPI

from apps.api.routes import datasets, languages, llms, models, system

api = NinjaAPI(title="LLM Benchmark Studio API", version="0.1.0")

api.add_router("/system", system.router)
api.add_router("/models", models.router)
api.add_router("/languages", languages.router)
api.add_router("/datasets", datasets.router)
api.add_router("/llms", llms.router)
