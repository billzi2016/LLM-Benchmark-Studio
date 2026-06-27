#!/usr/bin/env python3
"""Download default benchmark datasets into benchmark_datasets/raw.

This script uses the Hugging Face `datasets` package instead of custom
download code. Raw records are exported as JSONL so the parser can run without
depending on the datasets cache layout.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from datasets import load_dataset


DATA_DIR = Path(__file__).resolve().parent
RAW_DIR = DATA_DIR / "benchmark_datasets" / "raw"


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    hf_path: str
    hf_config: str | None
    split: str
    language: str = "en"
    activate: bool = True


DEFAULT_DATASETS: tuple[DatasetSpec, ...] = (
    DatasetSpec("mmlu", "cais/mmlu", "all", "test"),
    DatasetSpec("mmlu_pro", "TIGER-Lab/MMLU-Pro", None, "test"),
    DatasetSpec("arc_challenge", "allenai/ai2_arc", "ARC-Challenge", "test"),
    DatasetSpec("hellaswag", "Rowan/hellaswag", None, "validation"),
    DatasetSpec("truthfulqa", "truthfulqa/truthful_qa", "multiple_choice", "validation"),
    DatasetSpec("gsm8k", "openai/gsm8k", "main", "test"),
    DatasetSpec("bbh", "lukaemon/bbh", "boolean_expressions", "test"),
    DatasetSpec("winogrande", "allenai/winogrande", "winogrande_xl", "validation"),
    DatasetSpec("openbookqa", "allenai/openbookqa", "main", "test"),
)


def iter_specs(keys: list[str] | None) -> Iterable[DatasetSpec]:
    if not keys:
        return DEFAULT_DATASETS
    selected = set(keys)
    specs = [spec for spec in DEFAULT_DATASETS if spec.key in selected]
    missing = selected - {spec.key for spec in specs}
    if missing:
        raise SystemExit(f"Unknown dataset key(s): {', '.join(sorted(missing))}")
    return specs


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def download_spec(spec: DatasetSpec, limit: int | None, force: bool) -> dict:
    dataset_dir = RAW_DIR / spec.key
    dataset_dir.mkdir(parents=True, exist_ok=True)
    output_path = dataset_dir / f"{spec.split}.jsonl"
    manifest_path = dataset_dir / "manifest.json"

    if output_path.exists() and not force:
        return {
            **asdict(spec),
            "raw_path": str(output_path.relative_to(DATA_DIR)),
            "manifest_path": str(manifest_path.relative_to(DATA_DIR)),
            "status": "skipped",
            "count": sum(1 for _ in output_path.open("r", encoding="utf-8")),
        }

    try:
        if spec.hf_config:
            ds = load_dataset(spec.hf_path, spec.hf_config, split=spec.split)
        else:
            ds = load_dataset(spec.hf_path, split=spec.split)

        if limit is not None:
            ds = ds.select(range(min(limit, len(ds))))

        count = write_jsonl(output_path, ds)
        manifest = {
            **asdict(spec),
            "raw_path": str(output_path.relative_to(DATA_DIR)),
            "count": count,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return {**manifest, "manifest_path": str(manifest_path.relative_to(DATA_DIR)), "status": "downloaded"}
    except Exception as exc:
        return {
            **asdict(spec),
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download default benchmark datasets.")
    parser.add_argument(
        "--dataset",
        action="append",
        choices=[spec.key for spec in DEFAULT_DATASETS],
        help="Dataset key to download. Repeat for multiple datasets. Defaults to all.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional max rows per dataset.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing raw JSONL files.")
    parser.add_argument("--list", action="store_true", help="List available dataset keys and exit.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list:
        for spec in DEFAULT_DATASETS:
            print(f"{spec.key}\t{spec.hf_path}\t{spec.hf_config or '-'}\t{spec.split}")
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    results = [download_spec(spec, args.limit, args.force) for spec in iter_specs(args.dataset)]
    summary_path = RAW_DIR / "download_manifest.json"
    summary_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
