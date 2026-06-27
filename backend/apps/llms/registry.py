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
