from __future__ import annotations

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="BenchmarkRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("paused", "Paused"), ("completed", "Completed"), ("stopped", "Stopped"), ("error", "Error")], default="pending", max_length=32)),
                ("language_code", models.CharField(max_length=32)),
                ("provider_name", models.CharField(max_length=64)),
                ("judge_provider", models.CharField(max_length=64)),
                ("judge_model", models.CharField(max_length=128)),
                ("translate_provider", models.CharField(max_length=64)),
                ("translate_model", models.CharField(max_length=128)),
                ("total_tasks", models.PositiveIntegerField(default=0)),
                ("completed_tasks", models.PositiveIntegerField(default=0)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BenchmarkTask",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("paused", "Paused"), ("completed", "Completed"), ("stopped", "Stopped"), ("error", "Error")], default="pending", max_length=32)),
                ("task_kind", models.CharField(choices=[("benchmark", "Benchmark"), ("translate_then_benchmark", "Translate Then Benchmark")], default="benchmark", max_length=64)),
                ("model_name", models.CharField(max_length=128)),
                ("dataset_name", models.CharField(max_length=128)),
                ("dataset_display_name", models.CharField(max_length=128)),
                ("language_code", models.CharField(max_length=32)),
                ("source_language", models.CharField(max_length=32)),
                ("needs_translation", models.BooleanField(default=False)),
                ("total_questions", models.PositiveIntegerField(default=0)),
                ("completed_questions", models.PositiveIntegerField(default=0)),
                ("progress_percent", models.PositiveIntegerField(default=0)),
                ("eta_seconds", models.PositiveIntegerField(default=0)),
                ("model_group_order", models.PositiveIntegerField(default=0)),
                ("dataset_order", models.PositiveIntegerField(default=0)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("elapsed_seconds", models.PositiveIntegerField(default=0)),
                ("walltime_seconds", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="benchmarking.benchmarkrun")),
            ],
            options={"ordering": ["model_group_order", "dataset_order", "created_at"]},
        ),
        migrations.CreateModel(
            name="QuestionResult",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("sample_id", models.CharField(max_length=128)),
                ("question_index", models.PositiveIntegerField(default=0)),
                ("prompt_text", models.TextField(blank=True, default="")),
                ("translated_question", models.JSONField(blank=True, null=True)),
                ("llm_response", models.JSONField(blank=True, default=dict)),
                ("llm_judge", models.JSONField(blank=True, default=dict)),
                ("regex_judge", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="benchmarking.benchmarktask")),
            ],
            options={"ordering": ["question_index", "id"]},
        ),
        migrations.AddConstraint(
            model_name="benchmarktask",
            constraint=models.UniqueConstraint(fields=("run", "model_name", "dataset_name", "language_code"), name="unique_run_model_dataset_language"),
        ),
        migrations.AddConstraint(
            model_name="questionresult",
            constraint=models.UniqueConstraint(fields=("task", "sample_id"), name="unique_task_sample_id"),
        ),
    ]
