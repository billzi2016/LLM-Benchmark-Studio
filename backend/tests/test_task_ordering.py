from __future__ import annotations

from django.test import SimpleTestCase

from apps.datasets.task_ordering import build_model_first_benchmark_plan


class TaskOrderingTests(SimpleTestCase):
    def test_benchmark_plan_groups_by_model_first(self) -> None:
        plan = build_model_first_benchmark_plan(
            model_ids=["model-a", "model-b"],
            dataset_sample_ids={
                "dataset-1": ["sample-1", "sample-2"],
                "dataset-2": ["sample-3"],
            },
        )

        self.assertEqual(
            [(item.model_id, item.dataset_id, item.sample_id) for item in plan],
            [
                ("model-a", "dataset-1", "sample-1"),
                ("model-a", "dataset-1", "sample-2"),
                ("model-a", "dataset-2", "sample-3"),
                ("model-b", "dataset-1", "sample-1"),
                ("model-b", "dataset-1", "sample-2"),
                ("model-b", "dataset-2", "sample-3"),
            ],
        )
        self.assertEqual([item.model_group_order for item in plan], [0, 0, 0, 1, 1, 1])
