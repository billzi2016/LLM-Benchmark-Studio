from __future__ import annotations

from celery import shared_task

from apps.benchmarking.services import execute_run


@shared_task(name="benchmarking.execute_run")
def execute_run_task(run_id: str) -> dict[str, str]:
    execute_run(run_id)
    return {"run_id": run_id}

