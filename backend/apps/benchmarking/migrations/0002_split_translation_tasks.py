from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("benchmarking", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="benchmarktask",
            name="unique_run_model_dataset_language",
        ),
        migrations.AlterField(
            model_name="benchmarktask",
            name="task_kind",
            field=models.CharField(
                choices=[
                    ("translation", "Translation"),
                    ("benchmark", "Benchmark"),
                ],
                default="benchmark",
                max_length=64,
            ),
        ),
        migrations.AddConstraint(
            model_name="benchmarktask",
            constraint=models.UniqueConstraint(
                fields=("run", "task_kind", "model_name", "dataset_name", "language_code"),
                name="unique_run_kind_model_dataset_language",
            ),
        ),
    ]
