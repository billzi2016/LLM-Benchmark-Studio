from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class BenchmarkTaskPlanItem:
    model_id: str
    dataset_id: str
    sample_id: str
    model_group_order: int
    dataset_order: int
    sample_order: int


def build_model_first_benchmark_plan(
    model_ids: Iterable[str],
    dataset_sample_ids: dict[str, list[str]],
) -> list[BenchmarkTaskPlanItem]:
    """Build benchmark tasks grouped by model to avoid repeated model loading."""
    plan: list[BenchmarkTaskPlanItem] = []
    for model_index, model_id in enumerate(model_ids):
        for dataset_index, (dataset_id, sample_ids) in enumerate(dataset_sample_ids.items()):
            for sample_index, sample_id in enumerate(sample_ids):
                plan.append(
                    BenchmarkTaskPlanItem(
                        model_id=model_id,
                        dataset_id=dataset_id,
                        sample_id=sample_id,
                        model_group_order=model_index,
                        dataset_order=dataset_index,
                        sample_order=sample_index,
                    )
                )
    return plan
