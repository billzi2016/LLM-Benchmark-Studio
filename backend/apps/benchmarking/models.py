from __future__ import annotations

import uuid

from django.db import models


class RunStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    PAUSED = "paused", "Paused"
    COMPLETED = "completed", "Completed"
    STOPPED = "stopped", "Stopped"
    ERROR = "error", "Error"


class TaskKind(models.TextChoices):
    TRANSLATION = "translation", "Translation"
    BENCHMARK = "benchmark", "Benchmark"


class BenchmarkRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=32, choices=RunStatus.choices, default=RunStatus.PENDING)
    language_code = models.CharField(max_length=32)
    provider_name = models.CharField(max_length=64)
    judge_provider = models.CharField(max_length=64)
    judge_model = models.CharField(max_length=128)
    translate_provider = models.CharField(max_length=64)
    translate_model = models.CharField(max_length=128)
    total_tasks = models.PositiveIntegerField(default=0)
    completed_tasks = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class BenchmarkTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(BenchmarkRun, related_name="tasks", on_delete=models.CASCADE)
    status = models.CharField(max_length=32, choices=RunStatus.choices, default=RunStatus.PENDING)
    task_kind = models.CharField(max_length=64, choices=TaskKind.choices, default=TaskKind.BENCHMARK)
    model_name = models.CharField(max_length=128)
    dataset_name = models.CharField(max_length=128)
    dataset_display_name = models.CharField(max_length=128)
    language_code = models.CharField(max_length=32)
    source_language = models.CharField(max_length=32)
    needs_translation = models.BooleanField(default=False)
    total_questions = models.PositiveIntegerField(default=0)
    completed_questions = models.PositiveIntegerField(default=0)
    progress_percent = models.PositiveIntegerField(default=0)
    eta_seconds = models.PositiveIntegerField(default=0)
    model_group_order = models.PositiveIntegerField(default=0)
    dataset_order = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    elapsed_seconds = models.PositiveIntegerField(default=0)
    walltime_seconds = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["model_group_order", "dataset_order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "task_kind", "model_name", "dataset_name", "language_code"],
                name="unique_run_kind_model_dataset_language",
            )
        ]


class QuestionResult(models.Model):
    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(BenchmarkTask, related_name="results", on_delete=models.CASCADE)
    sample_id = models.CharField(max_length=128)
    question_index = models.PositiveIntegerField(default=0)
    prompt_text = models.TextField(blank=True, default="")
    translated_question = models.JSONField(null=True, blank=True)
    llm_response = models.JSONField(default=dict, blank=True)
    llm_judge = models.JSONField(default=dict, blank=True)
    regex_judge = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["question_index", "id"]
        constraints = [
            models.UniqueConstraint(fields=["task", "sample_id"], name="unique_task_sample_id"),
        ]
