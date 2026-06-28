from __future__ import annotations

from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from apps.benchmarking.models import BenchmarkRun, RunStatus
from apps.benchmarking.services import RunSelection, create_run, serialize_run
from apps.benchmarking.tasks import execute_run_task
from apps.core.schemas import OkResponse

router = Router(tags=["tasks"])


class CreateRunRequest(Schema):
    model_names: list[str]
    dataset_names: list[str]
    language_codes: list[str] = []
    language_code: str | None = None


class PlayRunRequest(Schema):
    task_ids: list[str] = []


@router.get("/runs", response=OkResponse)
def list_runs(request):  # noqa: ANN001
    runs = BenchmarkRun.objects.prefetch_related("tasks").all()[:10]
    return {"ok": True, "data": [serialize_run(run) for run in runs], "meta": {"total": len(runs)}}


@router.post("/runs", response=OkResponse)
def create_task_run(request, payload: CreateRunRequest):  # noqa: ANN001
    language_codes = payload.language_codes or ([payload.language_code] if payload.language_code else [])
    run = create_run(
        RunSelection(
            model_names=payload.model_names,
            dataset_names=payload.dataset_names,
            language_codes=language_codes,
        )
    )
    return {"ok": True, "data": serialize_run(run), "meta": {}}


@router.get("/runs/{run_id}", response=OkResponse)
def get_run(request, run_id: str):  # noqa: ANN001
    run = get_object_or_404(BenchmarkRun.objects.prefetch_related("tasks"), id=run_id)
    return {"ok": True, "data": serialize_run(run), "meta": {}}


@router.post("/runs/{run_id}/play", response=OkResponse)
def play_run(request, run_id: str, payload: PlayRunRequest):  # noqa: ANN001
    run = get_object_or_404(BenchmarkRun, id=run_id)
    if run.status != RunStatus.COMPLETED:
        run.status = RunStatus.RUNNING
        run.error_message = ""
        run.save(update_fields=["status", "error_message", "updated_at"])
        execute_run_task.delay(str(run.id), payload.task_ids or None)
    run = BenchmarkRun.objects.prefetch_related("tasks").get(id=run_id)
    return {"ok": True, "data": serialize_run(run), "meta": {}}


@router.post("/runs/{run_id}/pause", response=OkResponse)
def pause_run(request, run_id: str):  # noqa: ANN001
    run = get_object_or_404(BenchmarkRun, id=run_id)
    if run.status == RunStatus.RUNNING:
        run.status = RunStatus.PAUSED
        run.save(update_fields=["status", "updated_at"])
        run.tasks.filter(status=RunStatus.RUNNING).update(status=RunStatus.PAUSED)
    run = BenchmarkRun.objects.prefetch_related("tasks").get(id=run_id)
    return {"ok": True, "data": serialize_run(run), "meta": {}}


@router.post("/runs/{run_id}/stop", response=OkResponse)
def stop_run(request, run_id: str):  # noqa: ANN001
    run = get_object_or_404(BenchmarkRun, id=run_id)
    if run.status not in {RunStatus.COMPLETED, RunStatus.ERROR}:
        run.status = RunStatus.STOPPED
        run.save(update_fields=["status", "updated_at"])
        run.tasks.exclude(status=RunStatus.COMPLETED).update(status=RunStatus.STOPPED)
    run = BenchmarkRun.objects.prefetch_related("tasks").get(id=run_id)
    return {"ok": True, "data": serialize_run(run), "meta": {}}
