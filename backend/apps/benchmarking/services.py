from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone as django_timezone

from apps.benchmarking.models import BenchmarkRun, BenchmarkTask, QuestionResult, RunStatus, TaskKind
from apps.core.logging import log_llm_walltime
from apps.datasets.catalog import load_dataset, scan_datasets
from apps.datasets.languages import load_languages
from apps.llms.providers import get_provider


@dataclass(frozen=True)
class RunSelection:
    model_names: list[str]
    dataset_names: list[str]
    language_codes: list[str]


def _language_map() -> dict[str, dict[str, Any]]:
    return {item["code"]: item for item in load_languages(settings.LANGUAGES_PATH)}


def _dataset_map() -> dict[str, dict[str, Any]]:
    return {item["dataset_name"]: item for item in scan_datasets(settings.BENCHMARK_DATASETS_DIR)}


def _format_choices(options: dict[str, str]) -> str:
    return "\n".join(f"{label}. {text}" for label, text in options.items())


def _safe_json_parse(value: str) -> dict[str, Any]:
    text = value.strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            payload = json.loads(match.group(0))
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}


def _normalize_final_answer(answer: str, valid_values: list[str] | None = None) -> str:
    text = (answer or "").strip()
    if not valid_values:
        return text
    valid_upper = {item.upper(): item for item in valid_values}
    option_match = re.search(r"\b([A-Z])\b", text.upper())
    if option_match and option_match.group(1) in valid_upper:
        return valid_upper[option_match.group(1)]
    compact = text.upper().strip()
    return valid_upper.get(compact, text)


def _regex_judge(gold_answer: str, final_answer: str, valid_values: list[str] | None = None) -> list[dict[str, Any]]:
    normalized = _normalize_final_answer(final_answer, valid_values)
    return [
        {
            "matched": normalized == gold_answer,
            "gold_answer": gold_answer,
            "model_answer": final_answer,
            "normalized_answer": normalized,
            "judge_type": "regex",
        }
    ]


def _build_translation_prompt(
    *,
    source_language: str,
    target_language: str,
    question_stem: str,
    options: dict[str, str],
) -> str:
    return (
        "Translate the benchmark question into the target language.\n"
        "Return strict JSON only with keys question_stem and options.\n"
        f"Source language: {source_language}\n"
        f"Target language: {target_language}\n"
        f"Question: {question_stem}\n"
        f"Options:\n{_format_choices(options)}\n"
        "JSON:"
    )


def _translate_question(
    *,
    provider_name: str,
    model_name: str,
    source_language: str,
    target_language: str,
    question_stem: str,
    options: dict[str, str],
) -> dict[str, Any]:
    provider = get_provider(provider_name, settings.LLM_PROVIDERS)
    started_at = datetime.now(timezone.utc)
    response = provider.generate(
        model=model_name,
        prompt=_build_translation_prompt(
            source_language=source_language,
            target_language=target_language,
            question_stem=question_stem,
            options=options,
        ),
        temperature=0.0,
        max_tokens=1024,
    )
    finished_at = datetime.now(timezone.utc)
    log_llm_walltime(
        provider=provider_name,
        model=model_name,
        task_kind="translation",
        prompt_length=len(question_stem) + sum(len(text) for text in options.values()),
        started_at=started_at,
        finished_at=finished_at,
        language_code=target_language,
    )
    payload = _safe_json_parse(response.get("final_answer", ""))
    translated_options = payload.get("options")
    if not isinstance(translated_options, dict):
        translated_options = options
    return {
        "question_stem": str(payload.get("question_stem") or question_stem),
        "options": {str(key): str(value) for key, value in translated_options.items()},
        "raw_response": response,
    }


def _build_judge_prompt(
    *,
    question_stem: str,
    options: dict[str, str],
    gold_answer: str,
    model_answer: str,
) -> str:
    return (
        "You are judging a benchmark answer.\n"
        "Return strict JSON only with keys match (true/false), normalized_model_answer, reason.\n"
        f"Question: {question_stem}\n"
        f"Options:\n{_format_choices(options)}\n"
        f"Gold answer: {gold_answer}\n"
        f"Model answer: {model_answer}\n"
        "JSON:"
    )


def _judge_answer(
    *,
    judge_provider: str,
    judge_model: str,
    question_stem: str,
    options: dict[str, str],
    gold_answer: str,
    model_answer: str,
    valid_values: list[str] | None,
) -> dict[str, Any]:
    provider = get_provider(judge_provider, settings.LLM_PROVIDERS)
    started_at = datetime.now(timezone.utc)
    response = provider.generate(
        model=judge_model,
        prompt=_build_judge_prompt(
            question_stem=question_stem,
            options=options,
            gold_answer=gold_answer,
            model_answer=model_answer,
        ),
        temperature=0.0,
        max_tokens=256,
    )
    finished_at = datetime.now(timezone.utc)
    log_llm_walltime(
        provider=judge_provider,
        model=judge_model,
        task_kind="judge",
        prompt_length=len(question_stem) + sum(len(text) for text in options.values()),
        started_at=started_at,
        finished_at=finished_at,
    )
    parsed = _safe_json_parse(response.get("final_answer", ""))
    regex_match = _regex_judge(gold_answer, model_answer, valid_values)[0]["matched"]
    return {
        "judge_provider": judge_provider,
        "judge_model": judge_model,
        "match": bool(parsed.get("match", regex_match)),
        "normalized_model_answer": parsed.get("normalized_model_answer")
        or _normalize_final_answer(model_answer, valid_values),
        "reason": str(parsed.get("reason") or ""),
        "raw_response": response,
        "parsed": parsed,
    }


def serialize_task(task: BenchmarkTask, run_created_at: datetime | None = None) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "run_group_id": str(task.run_id),
        "run_created_at": run_created_at.isoformat() if run_created_at else None,
        "language_code": task.language_code,
        "needs_translation": task.needs_translation,
        "task_kind": task.task_kind,
        "status": task.status,
        "eta_seconds": task.eta_seconds,
        "model_name": task.model_name,
        "dataset_name": task.dataset_name,
        "dataset_display_name": task.dataset_display_name,
        "total_questions": task.total_questions,
        "completed_questions": task.completed_questions,
        "model_group_order": task.model_group_order,
        "dataset_order": task.dataset_order,
        "progress_percent": task.progress_percent,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "elapsed_seconds": task.elapsed_seconds,
        "walltime_seconds": task.walltime_seconds,
        "source_language": task.source_language,
        "error_message": task.error_message,
    }


def serialize_run(run: BenchmarkRun) -> dict[str, Any]:
    tasks = [
        serialize_task(task, run.created_at)
        for task in run.tasks.all().order_by("model_group_order", "dataset_order", "language_code", "created_at")
    ]
    return {
        "id": str(run.id),
        "status": run.status,
        "language_code": run.language_code,
        "provider_name": run.provider_name,
        "judge_provider": run.judge_provider,
        "judge_model": run.judge_model,
        "translate_provider": run.translate_provider,
        "translate_model": run.translate_model,
        "total_tasks": run.total_tasks,
        "completed_tasks": run.completed_tasks,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error_message": run.error_message,
        "tasks": tasks,
    }


def _clone_existing_completed_results(source_task: BenchmarkTask, target_task: BenchmarkTask) -> None:
    cloned_results = [
        QuestionResult(
            task=target_task,
            sample_id=result.sample_id,
            question_index=result.question_index,
            prompt_text=result.prompt_text,
            translated_question=result.translated_question,
            llm_response=result.llm_response,
            llm_judge=result.llm_judge,
            regex_judge=result.regex_judge,
        )
        for result in source_task.results.all().order_by("question_index", "id")
    ]
    if cloned_results:
        QuestionResult.objects.bulk_create(cloned_results)


def _apply_completed_clone(task: BenchmarkTask, cloned_from: BenchmarkTask) -> None:
    task.status = RunStatus.COMPLETED
    task.completed_questions = cloned_from.completed_questions
    task.progress_percent = 100
    task.eta_seconds = 0
    task.started_at = cloned_from.started_at or django_timezone.now()
    task.finished_at = cloned_from.finished_at or django_timezone.now()
    task.elapsed_seconds = cloned_from.elapsed_seconds
    task.walltime_seconds = cloned_from.walltime_seconds
    task.save(
        update_fields=[
            "status",
            "completed_questions",
            "progress_percent",
            "eta_seconds",
            "started_at",
            "finished_at",
            "elapsed_seconds",
            "walltime_seconds",
            "updated_at",
        ]
    )
    _clone_existing_completed_results(cloned_from, task)


@transaction.atomic
def create_run(selection: RunSelection) -> BenchmarkRun:
    datasets = _dataset_map()
    languages = _language_map()
    language_codes = list(dict.fromkeys(selection.language_codes))
    if not language_codes:
        raise ValueError("At least one language is required.")
    unknown_languages = [code for code in language_codes if code not in languages]
    if unknown_languages:
        raise ValueError(f"Unknown languages: {', '.join(unknown_languages)}")
    missing_datasets = [name for name in selection.dataset_names if name not in datasets]
    if missing_datasets:
        raise ValueError(f"Unknown datasets: {', '.join(missing_datasets)}")

    dataset_order_map = {name: index for index, name in enumerate(selection.dataset_names)}
    translation_specs: list[tuple[str, dict[str, Any], int]] = []
    benchmark_specs: list[tuple[str, dict[str, Any], int, str, int]] = []

    for language_code in language_codes:
        for dataset_name in selection.dataset_names:
            dataset = datasets[dataset_name]
            if str(dataset.get("source_language")) != language_code:
                translation_specs.append((language_code, dataset, dataset_order_map[dataset_name]))
        for model_index, model_name in enumerate(selection.model_names):
            for dataset_name in selection.dataset_names:
                benchmark_specs.append(
                    (
                        model_name,
                        datasets[dataset_name],
                        model_index,
                        language_code,
                        dataset_order_map[dataset_name],
                    )
                )

    run = BenchmarkRun.objects.create(
        language_code=language_codes[0] if len(language_codes) == 1 else "multi",
        provider_name=settings.DEFAULT_PROVIDER,
        judge_provider=settings.JUDGE_PROVIDER,
        judge_model=settings.JUDGE_MODEL,
        translate_provider=settings.TRANSLATE_PROVIDER,
        translate_model=settings.TRANSLATE_MODEL,
        total_tasks=len(translation_specs) + len(benchmark_specs),
    )

    completed_task_count = 0
    for language_code, dataset, dataset_order in translation_specs:
        dataset_name = str(dataset["dataset_name"])
        translation_task = BenchmarkTask.objects.create(
            run=run,
            model_name=settings.TRANSLATE_MODEL,
            dataset_name=dataset_name,
            dataset_display_name=str(dataset.get("display_name") or dataset_name),
            language_code=language_code,
            source_language=str(dataset.get("source_language") or "en"),
            needs_translation=True,
            task_kind=TaskKind.TRANSLATION,
            total_questions=int(dataset.get("question_count") or 0),
            model_group_order=0,
            dataset_order=dataset_order,
        )
        cloned_from = (
            BenchmarkTask.objects.filter(
                status=RunStatus.COMPLETED,
                task_kind=TaskKind.TRANSLATION,
                model_name=settings.TRANSLATE_MODEL,
                dataset_name=dataset_name,
                language_code=language_code,
            )
            .prefetch_related("results")
            .order_by("-finished_at", "-updated_at")
            .first()
        )
        if cloned_from:
            _apply_completed_clone(translation_task, cloned_from)
            completed_task_count += 1

    translation_offset = len(translation_specs) + 1
    for model_name, dataset, model_index, language_code, dataset_order in benchmark_specs:
        dataset_name = str(dataset["dataset_name"])
        benchmark_task = BenchmarkTask.objects.create(
            run=run,
            model_name=model_name,
            dataset_name=dataset_name,
            dataset_display_name=str(dataset.get("display_name") or dataset_name),
            language_code=language_code,
            source_language=str(dataset.get("source_language") or "en"),
            needs_translation=str(dataset.get("source_language")) != language_code,
            task_kind=TaskKind.BENCHMARK,
            total_questions=int(dataset.get("question_count") or 0),
            model_group_order=translation_offset + model_index,
            dataset_order=dataset_order,
        )
        cloned_from = (
            BenchmarkTask.objects.filter(
                status=RunStatus.COMPLETED,
                task_kind=TaskKind.BENCHMARK,
                model_name=model_name,
                dataset_name=dataset_name,
                language_code=language_code,
            )
            .prefetch_related("results")
            .order_by("-finished_at", "-updated_at")
            .first()
        )
        if cloned_from:
            _apply_completed_clone(benchmark_task, cloned_from)
            completed_task_count += 1

    run.completed_tasks = completed_task_count
    if completed_task_count == run.total_tasks and run.total_tasks > 0:
        run.status = RunStatus.COMPLETED
        run.started_at = django_timezone.now()
        run.finished_at = run.started_at
    run.save(
        update_fields=[
            "completed_tasks",
            "status",
            "started_at",
            "finished_at",
            "updated_at",
        ]
    )
    return BenchmarkRun.objects.prefetch_related("tasks").get(id=run.id)


def _update_task_progress(task: BenchmarkTask) -> None:
    task.progress_percent = (
        0 if task.total_questions == 0 else round((task.completed_questions / task.total_questions) * 100)
    )
    remaining = max(0, task.total_questions - task.completed_questions)
    average_seconds = task.elapsed_seconds / max(task.completed_questions, 1)
    task.eta_seconds = int(round(remaining * average_seconds)) if task.completed_questions else 0


def _mark_run_status_from_tasks(run: BenchmarkRun) -> None:
    statuses = list(run.tasks.values_list("status", flat=True))
    run.completed_tasks = sum(1 for status in statuses if status == RunStatus.COMPLETED)
    if statuses and all(status == RunStatus.COMPLETED for status in statuses):
        run.status = RunStatus.COMPLETED
        if not run.finished_at:
            run.finished_at = django_timezone.now()
    run.save(update_fields=["completed_tasks", "status", "finished_at", "updated_at"])


def execute_run(run_id: str, task_ids: list[str] | None = None) -> BenchmarkRun:
    run = BenchmarkRun.objects.prefetch_related("tasks").get(id=run_id)
    if run.status == RunStatus.COMPLETED:
        return run
    if not run.started_at:
        run.started_at = django_timezone.now()
    run.status = RunStatus.RUNNING
    run.error_message = ""
    run.save(update_fields=["started_at", "status", "error_message", "updated_at"])

    task_queryset = run.tasks.all()
    if task_ids:
        task_queryset = task_queryset.filter(id__in=task_ids)
    ordered_tasks = list(
        task_queryset.order_by("model_group_order", "dataset_order", "language_code", "created_at")
    )
    try:
        for task in ordered_tasks:
            run.refresh_from_db()
            if run.status in {RunStatus.PAUSED, RunStatus.STOPPED}:
                break
            if task.status == RunStatus.COMPLETED:
                continue
            _execute_task(run, task.id)
            run.refresh_from_db()
            if run.status in {RunStatus.PAUSED, RunStatus.STOPPED, RunStatus.ERROR}:
                break
    except Exception as exc:  # noqa: BLE001
        run.status = RunStatus.ERROR
        run.error_message = f"{exc.__class__.__name__}: {exc}"
        run.finished_at = django_timezone.now()
        run.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        raise
    run.refresh_from_db()
    if run.status == RunStatus.RUNNING:
        _mark_run_status_from_tasks(run)
    return BenchmarkRun.objects.prefetch_related("tasks").get(id=run.id)


def _begin_task(run: BenchmarkRun, task: BenchmarkTask, questions: list[dict[str, Any]]) -> None:
    if task.total_questions != len(questions):
        task.total_questions = len(questions)
        task.save(update_fields=["total_questions", "updated_at"])
    if not task.started_at:
        task.started_at = django_timezone.now()
    task.status = RunStatus.RUNNING
    task.error_message = ""
    task.save(update_fields=["started_at", "status", "error_message", "updated_at"])


def _handle_run_pause_stop(run: BenchmarkRun, task: BenchmarkTask) -> bool:
    run.refresh_from_db()
    task.refresh_from_db()
    if run.status == RunStatus.PAUSED:
        task.status = RunStatus.PAUSED
        task.save(update_fields=["status", "updated_at"])
        return True
    if run.status == RunStatus.STOPPED:
        task.status = RunStatus.STOPPED
        task.finished_at = django_timezone.now()
        task.save(update_fields=["status", "finished_at", "updated_at"])
        return True
    return False


def _complete_task(run: BenchmarkRun, task: BenchmarkTask) -> None:
    task.refresh_from_db()
    task.status = RunStatus.COMPLETED
    task.finished_at = django_timezone.now()
    if task.started_at:
        task.elapsed_seconds = int((task.finished_at - task.started_at).total_seconds())
        task.walltime_seconds = task.elapsed_seconds
    task.completed_questions = QuestionResult.objects.filter(task=task).count()
    task.progress_percent = 100
    task.eta_seconds = 0
    task.save(
        update_fields=[
            "status",
            "finished_at",
            "elapsed_seconds",
            "walltime_seconds",
            "completed_questions",
            "progress_percent",
            "eta_seconds",
            "updated_at",
        ]
    )
    run.refresh_from_db()
    run.completed_tasks = run.tasks.filter(status=RunStatus.COMPLETED).count()
    run.save(update_fields=["completed_tasks", "updated_at"])


def _execute_task(run: BenchmarkRun, task_id: Any) -> None:
    task = BenchmarkTask.objects.get(id=task_id)
    if task.task_kind == TaskKind.TRANSLATION:
        _execute_translation_task(run, task)
        return
    _execute_benchmark_task(run, task)


def _execute_translation_task(run: BenchmarkRun, task: BenchmarkTask) -> None:
    dataset = load_dataset(settings.BENCHMARK_DATASETS_DIR, task.dataset_name)
    questions = [item for item in dataset["questions"] if item.get("activate", True)]
    _begin_task(run, task, questions)

    existing_results = {result.sample_id for result in QuestionResult.objects.filter(task=task).only("sample_id")}
    for question_index, item in enumerate(questions):
        if _handle_run_pause_stop(run, task):
            return
        sample_id = str(item["sample_id"])
        if sample_id in existing_results:
            continue
        question = item["question"]
        question_stem = str(question["question_stem"])
        options = {str(key): str(value) for key, value in dict(question["options"]).items()}
        translated_question = _translate_question(
            provider_name=run.translate_provider,
            model_name=run.translate_model,
            source_language=task.source_language,
            target_language=task.language_code,
            question_stem=question_stem,
            options=options,
        )
        QuestionResult.objects.create(
            task=task,
            sample_id=sample_id,
            question_index=question_index,
            prompt_text=_build_translation_prompt(
                source_language=task.source_language,
                target_language=task.language_code,
                question_stem=question_stem,
                options=options,
            ),
            translated_question={
                "question_stem": translated_question["question_stem"],
                "options": translated_question["options"],
            },
            llm_response=translated_question["raw_response"],
            llm_judge={},
            regex_judge=[],
        )
        task.completed_questions = QuestionResult.objects.filter(task=task).count()
        if task.started_at:
            elapsed = int((django_timezone.now() - task.started_at).total_seconds())
            task.elapsed_seconds = max(0, elapsed)
            task.walltime_seconds = task.elapsed_seconds
        _update_task_progress(task)
        task.save(
            update_fields=[
                "completed_questions",
                "elapsed_seconds",
                "walltime_seconds",
                "progress_percent",
                "eta_seconds",
                "updated_at",
            ]
        )
    _complete_task(run, task)


def _translation_result_map(run: BenchmarkRun, task: BenchmarkTask) -> dict[str, dict[str, Any]]:
    translation_task = (
        BenchmarkTask.objects.filter(
            run=run,
            task_kind=TaskKind.TRANSLATION,
            dataset_name=task.dataset_name,
            language_code=task.language_code,
            status=RunStatus.COMPLETED,
        )
        .prefetch_related("results")
        .first()
    )
    if not translation_task:
        raise RuntimeError(f"Missing translation task for {task.dataset_name}:{task.language_code}")
    return {
        result.sample_id: dict(result.translated_question or {})
        for result in translation_task.results.all()
        if result.translated_question
    }


def _execute_benchmark_task(run: BenchmarkRun, task: BenchmarkTask) -> None:
    dataset = load_dataset(settings.BENCHMARK_DATASETS_DIR, task.dataset_name)
    source = dataset["source"]
    questions = [item for item in dataset["questions"] if item.get("activate", True)]
    _begin_task(run, task, questions)

    valid_values = list((source.get("answer_format") or {}).get("valid_values") or [])
    existing_results = {result.sample_id for result in QuestionResult.objects.filter(task=task).only("sample_id")}
    translated_map = _translation_result_map(run, task) if task.needs_translation else {}

    for question_index, item in enumerate(questions):
        if _handle_run_pause_stop(run, task):
            return
        sample_id = str(item["sample_id"])
        if sample_id in existing_results:
            continue
        question = item["question"]
        question_stem = str(question["question_stem"])
        options = {str(key): str(value) for key, value in dict(question["options"]).items()}
        translated_question = None
        runtime_stem = question_stem
        runtime_options = options
        if task.needs_translation:
            translated_question = translated_map.get(sample_id)
            if not translated_question:
                raise RuntimeError(
                    f"Missing translated question for {task.dataset_name}:{sample_id}:{task.language_code}"
                )
            runtime_stem = str(translated_question.get("question_stem") or question_stem)
            runtime_options = {
                str(key): str(value)
                for key, value in dict(translated_question.get("options") or options).items()
            }

        prompt_text = str(source["benchmark_prompt"]).format(
            question=runtime_stem,
            choices=_format_choices(runtime_options),
        )
        provider = get_provider(run.provider_name, settings.LLM_PROVIDERS)
        started_at = datetime.now(timezone.utc)
        response = provider.generate(
            model=task.model_name,
            prompt=prompt_text,
            temperature=0.0,
            max_tokens=256,
        )
        finished_at = datetime.now(timezone.utc)
        log_llm_walltime(
            provider=run.provider_name,
            model=task.model_name,
            task_kind=task.task_kind,
            prompt_length=len(prompt_text),
            started_at=started_at,
            finished_at=finished_at,
            dataset_name=task.dataset_name,
            language_code=task.language_code,
        )
        final_answer = _normalize_final_answer(response.get("final_answer", ""), valid_values)
        llm_response = {
            **response,
            "final_answer": final_answer,
            "task_kind": task.task_kind,
            "language_code": task.language_code,
        }
        regex_judge = _regex_judge(str(question["answer"]), final_answer, valid_values)
        llm_judge = _judge_answer(
            judge_provider=run.judge_provider,
            judge_model=run.judge_model,
            question_stem=runtime_stem,
            options=runtime_options,
            gold_answer=str(question["answer"]),
            model_answer=final_answer,
            valid_values=valid_values,
        )
        QuestionResult.objects.create(
            task=task,
            sample_id=sample_id,
            question_index=question_index,
            prompt_text=prompt_text,
            translated_question=translated_question,
            llm_response=llm_response,
            llm_judge=llm_judge,
            regex_judge=regex_judge,
        )
        task.completed_questions = QuestionResult.objects.filter(task=task).count()
        if task.started_at:
            elapsed = int((django_timezone.now() - task.started_at).total_seconds())
            task.elapsed_seconds = max(0, elapsed)
            task.walltime_seconds = task.elapsed_seconds
        _update_task_progress(task)
        task.save(
            update_fields=[
                "completed_questions",
                "elapsed_seconds",
                "walltime_seconds",
                "progress_percent",
                "eta_seconds",
                "updated_at",
            ]
        )
    _complete_task(run, task)
