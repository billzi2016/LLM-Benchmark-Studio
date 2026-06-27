from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def safe_dataset_path(dataset_dir: Path, dataset_name: str) -> Path:
    if "/" in dataset_name or "\\" in dataset_name or dataset_name.startswith("."):
        raise ValueError("Invalid dataset name.")
    path = (dataset_dir / f"{dataset_name}.json").resolve()
    dataset_root = dataset_dir.resolve()
    if dataset_root not in path.parents:
        raise ValueError("Dataset path escapes benchmark dataset directory.")
    return path


def scan_datasets(dataset_dir: Path) -> list[dict[str, Any]]:
    if not dataset_dir.exists():
        return []
    datasets: list[dict[str, Any]] = []
    for path in sorted(dataset_dir.glob("*.json")):
        payload = read_json(path)
        source = payload.get("source", {})
        questions = payload.get("questions", [])
        datasets.append(
            {
                "dataset_name": source.get("dataset_name", path.stem),
                "display_name": source.get("display_name", path.stem),
                "subset": source.get("subset"),
                "source_language": source.get("source_language"),
                "task_type": source.get("task_type"),
                "activate": source.get("activate", True),
                "question_count": len(questions),
                "path": str(path),
            }
        )
    return datasets


def load_dataset(dataset_dir: Path, dataset_name: str) -> dict[str, Any]:
    path = safe_dataset_path(dataset_dir, dataset_name)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_name}")
    return read_json(path)
