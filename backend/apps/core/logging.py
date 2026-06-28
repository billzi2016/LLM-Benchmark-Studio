from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


llm_walltime_logger = logging.getLogger("llm_walltime")


def log_llm_walltime(
    *,
    provider: str,
    model: str,
    task_kind: str,
    prompt_length: int,
    started_at: datetime,
    finished_at: datetime,
    dataset_name: str = "",
    language_code: str = "",
) -> None:
    payload = {
        "timestamp": finished_at.astimezone(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "task_kind": task_kind,
        "dataset_name": dataset_name,
        "language_code": language_code,
        "started_at": started_at.astimezone(timezone.utc).isoformat(),
        "finished_at": finished_at.astimezone(timezone.utc).isoformat(),
        "elapsed_seconds": round((finished_at - started_at).total_seconds(), 3),
        "walltime_seconds": round((finished_at - started_at).total_seconds(), 3),
        "prompt_length": prompt_length,
    }
    llm_walltime_logger.info(json.dumps(payload, ensure_ascii=True, sort_keys=True))
