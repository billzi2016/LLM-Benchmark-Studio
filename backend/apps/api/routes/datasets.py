from __future__ import annotations

from django.conf import settings
from ninja import Router

from apps.core.schemas import OkResponse
from apps.datasets.catalog import load_dataset, scan_datasets

router = Router(tags=["datasets"])


@router.get("", response=OkResponse)
def list_datasets(request, include_inactive: bool = True):  # noqa: ANN001
    datasets = scan_datasets(settings.BENCHMARK_DATASETS_DIR)
    if not include_inactive:
        datasets = [dataset for dataset in datasets if dataset.get("activate")]
    return {"ok": True, "data": datasets, "meta": {"total": len(datasets)}}


@router.get("/{dataset_name}", response=OkResponse)
def get_dataset(request, dataset_name: str, include_questions: bool = False):  # noqa: ANN001
    dataset = load_dataset(settings.BENCHMARK_DATASETS_DIR, dataset_name)
    if not include_questions:
        dataset = {**dataset, "questions": []}
    return {"ok": True, "data": dataset, "meta": {}}
