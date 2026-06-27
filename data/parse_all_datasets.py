#!/usr/bin/env python3
"""Parse raw benchmark JSONL exports into the studio JSON format."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent
BENCHMARK_DIR = DATA_DIR / "benchmark_datasets"
RAW_DIR = BENCHMARK_DIR / "raw"
RULES_PATH = DATA_DIR / "parser_json_rules.json"


def load_rules() -> dict[str, Any]:
    if not RULES_PATH.exists():
        return {}
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    return {rule["dataset_key"]: rule for rule in rules.get("datasets", [])}


PARSER_RULES = load_rules()


def rule_for(dataset_key: str) -> dict[str, Any]:
    return PARSER_RULES.get(dataset_key, {})


def benchmark_prompt_for(dataset_key: str) -> str:
    rule = rule_for(dataset_key)
    return rule.get("benchmark_prompt") or rule.get("prompt_template", "")


def judge_prompt_for(dataset_key: str) -> str:
    rule = rule_for(dataset_key)
    return rule.get(
        "judge_prompt",
        "You are judging whether a model answer matches the gold answer for a benchmark question. "
        "Use the question stem, options, gold answer, and model answer. Return strict JSON only.",
    )


def regex_judge_rule_for(dataset_key: str) -> dict[str, Any]:
    rule = rule_for(dataset_key)
    return rule.get(
        "regex_judge_rule",
        {
            "purpose": "Run a deterministic regex-based judge against an existing llm_response without overwriting llm_judge.",
            "write_target": "regex_judge[]",
            "must_not_modify": ["question", "llm_response", "llm_judge"],
        },
    )


def task_type_for(dataset_key: str) -> str:
    return rule_for(dataset_key).get("task_type", "unknown")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def choice_map(values: list[Any]) -> dict[str, str]:
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return {labels[index]: str(value) for index, value in enumerate(values)}


def answer_from_index(index: Any) -> str:
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if isinstance(index, str) and index.strip().upper() in labels:
        return index.strip().upper()
    return labels[int(index)]


def normalize_mmlu(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "sample_id": f"mmlu-{index:08d}",
        "question": row["question"],
        "choices": choice_map(row["choices"]),
        "answer": answer_from_index(row["answer"]),
        "language": "en",
        "activate": True,
        "metadata": {
            "task_type": task_type_for("mmlu"),
            "subject": row.get("subject"),
        },
    }


def normalize_mmlu_pro(row: dict[str, Any], index: int) -> dict[str, Any]:
    options = row.get("options") or row.get("choices") or []
    return {
        "sample_id": f"mmlu_pro-{index:08d}",
        "question": row.get("question", ""),
        "choices": choice_map(options),
        "answer": str(row.get("answer", "")).strip().upper(),
        "language": "en",
        "activate": True,
        "metadata": {
            "task_type": task_type_for("mmlu_pro"),
            "category": row.get("category"),
            "src": row.get("src"),
        },
    }


def normalize_arc(row: dict[str, Any], index: int) -> dict[str, Any]:
    labels = row["choices"]["label"]
    texts = row["choices"]["text"]
    choices = {str(label).upper(): str(text) for label, text in zip(labels, texts, strict=False)}
    return {
        "sample_id": f"arc_challenge-{index:08d}",
        "question": row["question"],
        "choices": choices,
        "answer": str(row["answerKey"]).strip().upper(),
        "language": "en",
        "activate": True,
        "metadata": {
            "task_type": task_type_for("arc_challenge"),
            "id": row.get("id"),
        },
    }


def normalize_hellaswag(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "sample_id": f"hellaswag-{index:08d}",
        "question": f"{row.get('ctx', '')}".strip(),
        "choices": choice_map(row.get("endings", [])),
        "answer": answer_from_index(row["label"]),
        "language": "en",
        "activate": True,
        "metadata": {
            "task_type": task_type_for("hellaswag"),
            "activity_label": row.get("activity_label"),
            "source_id": row.get("source_id"),
        },
    }


def normalize_truthfulqa(row: dict[str, Any], index: int) -> dict[str, Any]:
    choices = row.get("mc1_targets", {}).get("choices") or row.get("mc2_targets", {}).get("choices") or []
    labels = row.get("mc1_targets", {}).get("labels") or row.get("mc2_targets", {}).get("labels") or []
    answer_index = labels.index(1) if 1 in labels else 0
    return {
        "sample_id": f"truthfulqa-{index:08d}",
        "question": row["question"],
        "choices": choice_map(choices),
        "answer": answer_from_index(answer_index),
        "language": "en",
        "activate": True,
        "metadata": {
            "task_type": task_type_for("truthfulqa"),
            "category": row.get("category"),
        },
    }


def normalize_gsm8k(row: dict[str, Any], index: int) -> dict[str, Any]:
    answer = str(row.get("answer", ""))
    match = re.search(r"####\s*([-+]?\d[\d,]*(?:\.\d+)?)", answer)
    final_answer = match.group(1).replace(",", "") if match else answer.strip()
    return {
        "sample_id": f"gsm8k-{index:08d}",
        "question": row["question"],
        "choices": {},
        "answer": final_answer,
        "language": "en",
        "activate": True,
        "metadata": {
            "task_type": task_type_for("gsm8k"),
            "raw_answer": answer,
            "answer_type": "numeric",
        },
    }


def normalize_bbh(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "sample_id": f"bbh-{index:08d}",
        "question": row.get("input", ""),
        "choices": {},
        "answer": str(row.get("target", "")).strip(),
        "language": "en",
        "activate": True,
        "metadata": {
            "task_type": task_type_for("bbh"),
            "answer_type": "free_form",
        },
    }


def normalize_winogrande(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "sample_id": f"winogrande-{index:08d}",
        "question": row["sentence"],
        "choices": {"A": row["option1"], "B": row["option2"]},
        "answer": answer_from_index(int(row["answer"]) - 1),
        "language": "en",
        "activate": True,
        "metadata": {
            "task_type": task_type_for("winogrande"),
        },
    }


def normalize_openbookqa(row: dict[str, Any], index: int) -> dict[str, Any]:
    labels = row["choices"]["label"]
    texts = row["choices"]["text"]
    choices = {str(label).upper(): str(text) for label, text in zip(labels, texts, strict=False)}
    return {
        "sample_id": f"openbookqa-{index:08d}",
        "question": row["question_stem"],
        "choices": choices,
        "answer": str(row["answerKey"]).strip().upper(),
        "language": "en",
        "activate": True,
        "metadata": {
            "task_type": task_type_for("openbookqa"),
            "id": row.get("id"),
        },
    }


NORMALIZERS = {
    "mmlu": normalize_mmlu,
    "mmlu_pro": normalize_mmlu_pro,
    "arc_challenge": normalize_arc,
    "hellaswag": normalize_hellaswag,
    "truthfulqa": normalize_truthfulqa,
    "gsm8k": normalize_gsm8k,
    "bbh": normalize_bbh,
    "winogrande": normalize_winogrande,
    "openbookqa": normalize_openbookqa,
}


def build_question_item(raw_sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": raw_sample["sample_id"],
        "language": raw_sample["language"],
        "activate": raw_sample["activate"],
        "question": {
            "question_stem": raw_sample["question"],
            "options": raw_sample["choices"],
            "answer": raw_sample["answer"],
        },
        "llm_response": {},
        "llm_judge": {},
        "regex_judge": [],
        "metadata": raw_sample.get("metadata", {}),
    }


def parse_dataset(dataset_key: str, force: bool) -> dict[str, Any]:
    manifest_path = RAW_DIR / dataset_key / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing raw manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_path = DATA_DIR / manifest["raw_path"]
    output_path = BENCHMARK_DIR / f"{dataset_key}.json"
    if output_path.exists() and not force:
        return {
            "dataset_name": dataset_key,
            "status": "skipped",
            "output_path": str(output_path.relative_to(DATA_DIR)),
        }

    rows = read_jsonl(raw_path)
    normalizer = NORMALIZERS[dataset_key]
    questions = [build_question_item(normalizer(row, index)) for index, row in enumerate(rows, start=1)]
    rule = rule_for(dataset_key)
    payload = {
        "source": {
            "dataset_name": dataset_key,
            "display_name": rule.get("dataset_name", dataset_key),
            "subset": manifest.get("hf_config") or manifest.get("split") or "default",
            "source_language": manifest.get("language", "en"),
            "activate": manifest.get("activate", True),
            "task_type": task_type_for(dataset_key),
            "answer_format": rule.get("answer_format", {}),
            "raw_source": {
                "type": "huggingface",
                "hf_path": manifest.get("hf_path"),
                "hf_config": manifest.get("hf_config"),
                "split": manifest.get("split"),
                "raw_path": manifest.get("raw_path"),
            },
            "field_mapping": rule.get("field_mapping", {}),
            "metadata_keep_fields": rule.get("metadata_keep_fields", []),
            "ignored_fields": rule.get("ignored_fields", []),
            "benchmark_prompt": benchmark_prompt_for(dataset_key),
            "judge_prompt": judge_prompt_for(dataset_key),
            "regex_judge_rule": regex_judge_rule_for(dataset_key),
        },
        "questions": questions,
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "dataset_name": dataset_key,
        "status": "parsed",
        "question_count": len(questions),
        "output_path": str(output_path.relative_to(DATA_DIR)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse raw benchmark datasets into studio JSON.")
    parser.add_argument(
        "--dataset",
        action="append",
        choices=sorted(NORMALIZERS),
        help="Dataset key to parse. Repeat for multiple datasets. Defaults to every raw manifest found.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing normalized JSON files.")
    parser.add_argument("--list", action="store_true", help="List supported dataset keys and exit.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list:
        for key in sorted(NORMALIZERS):
            print(key)
        return

    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    if args.dataset:
        dataset_keys = args.dataset
    else:
        dataset_keys = sorted(path.name for path in RAW_DIR.iterdir() if (path / "manifest.json").exists())

    results = [parse_dataset(dataset_key, args.force) for dataset_key in dataset_keys]
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
