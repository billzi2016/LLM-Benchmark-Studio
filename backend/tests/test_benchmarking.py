from __future__ import annotations

import json
from unittest.mock import patch

from django.test import TestCase

from apps.benchmarking.models import BenchmarkRun, QuestionResult
from apps.benchmarking.services import execute_run


class BenchmarkingApiTests(TestCase):
    def setUp(self) -> None:
        self.dataset = {
            "source": {
                "dataset_name": "toyset",
                "display_name": "Toy Set",
                "source_language": "en",
                "benchmark_prompt": "Question:\n{question}\n\nChoices:\n{choices}\n\nAnswer:",
                "answer_format": {"valid_values": ["A", "B", "C", "D"]},
            },
            "questions": [
                {
                    "sample_id": "toy-1",
                    "activate": True,
                    "question": {
                        "question_stem": "2 + 2 = ?",
                        "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                        "answer": "B",
                    },
                }
            ],
        }
        self.client.defaults["CONTENT_TYPE"] = "application/json"

    @patch("apps.benchmarking.services.scan_datasets")
    @patch("apps.benchmarking.services.load_languages")
    def test_create_run_sorts_translation_tasks_first(self, mock_languages, mock_scan_datasets) -> None:
        mock_languages.return_value = [{"code": "fr", "activate": True}]
        mock_scan_datasets.return_value = [
            {
                "dataset_name": "english_set",
                "display_name": "English Set",
                "source_language": "en",
                "question_count": 1,
            },
            {
                "dataset_name": "french_set",
                "display_name": "French Set",
                "source_language": "fr",
                "question_count": 1,
            },
        ]

        response = self.client.post(
            "/api/tasks/runs",
            data=json.dumps(
                {
                    "model_names": ["gpt-oss:20b"],
                    "dataset_names": ["english_set", "french_set"],
                    "language_codes": ["fr"],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        tasks = response.json()["data"]["tasks"]
        self.assertEqual(tasks[0]["task_kind"], "translation")
        self.assertEqual(tasks[0]["dataset_name"], "english_set")
        self.assertEqual(tasks[1]["task_kind"], "benchmark")
        self.assertEqual(tasks[2]["task_kind"], "benchmark")

    @patch("apps.benchmarking.services.get_provider")
    @patch("apps.benchmarking.services.load_dataset")
    @patch("apps.benchmarking.services.scan_datasets")
    @patch("apps.benchmarking.services.load_languages")
    def test_play_run_executes_and_persists_results(
        self,
        mock_languages,
        mock_scan_datasets,
        mock_load_dataset,
        mock_get_provider,
    ) -> None:
        mock_languages.return_value = [{"code": "en", "activate": True}]
        mock_scan_datasets.return_value = [
            {
                "dataset_name": "toyset",
                "display_name": "Toy Set",
                "source_language": "en",
                "question_count": 1,
            }
        ]
        mock_load_dataset.return_value = self.dataset

        class FakeProvider:
            def __init__(self, final_answer: str) -> None:
                self.final_answer = final_answer

            def generate(self, model: str, prompt: str, temperature: float = 0.0, max_tokens: int = 128) -> dict[str, object]:
                return {
                    "provider": "fake",
                    "model": model,
                    "raw_response": self.final_answer,
                    "final_answer": self.final_answer,
                    "thinking_present": False,
                    "done": True,
                    "done_reason": "stop",
                    "usage": {},
                }

        def provider_factory(provider_name, provider_configs):  # type: ignore[no-untyped-def]
            if provider_name == "ollama":
                return FakeProvider("B")
            return FakeProvider('{"match": true, "normalized_model_answer": "B", "reason": "exact"}')

        mock_get_provider.side_effect = provider_factory

        create_response = self.client.post(
            "/api/tasks/runs",
            data=json.dumps(
                {
                    "model_names": ["gpt-oss:20b"],
                    "dataset_names": ["toyset"],
                    "language_codes": ["en"],
                }
            ),
            content_type="application/json",
        )
        run_id = create_response.json()["data"]["id"]

        execute_run(run_id)
        play_response = self.client.get(f"/api/tasks/runs/{run_id}")

        self.assertEqual(play_response.status_code, 200)
        payload = play_response.json()["data"]
        self.assertEqual(payload["status"], "completed")
        benchmark_task = next(task for task in payload["tasks"] if task["task_kind"] == "benchmark")
        self.assertEqual(benchmark_task["status"], "completed")
        self.assertEqual(benchmark_task["completed_questions"], 1)
        self.assertEqual(QuestionResult.objects.count(), 1)
        run = BenchmarkRun.objects.get(id=run_id)
        self.assertEqual(run.completed_tasks, 1)

    @patch("apps.benchmarking.services.scan_datasets")
    @patch("apps.benchmarking.services.load_languages")
    def test_create_run_reuses_completed_results_without_rerun(self, mock_languages, mock_scan_datasets) -> None:
        mock_languages.return_value = [{"code": "en", "activate": True}]
        mock_scan_datasets.return_value = [
            {
                "dataset_name": "toyset",
                "display_name": "Toy Set",
                "source_language": "en",
                "question_count": 1,
            }
        ]

        previous_run = BenchmarkRun.objects.create(
            language_code="en",
            provider_name="ollama",
            judge_provider="ollama",
            judge_model="gpt-oss:20b",
            translate_provider="ollama",
            translate_model="gpt-oss:20b",
            total_tasks=1,
            completed_tasks=1,
            status="completed",
        )
        previous_task = previous_run.tasks.create(
            status="completed",
            task_kind="benchmark",
            model_name="gpt-oss:20b",
            dataset_name="toyset",
            dataset_display_name="Toy Set",
            language_code="en",
            source_language="en",
            needs_translation=False,
            total_questions=1,
            completed_questions=1,
            progress_percent=100,
            elapsed_seconds=12,
            walltime_seconds=12,
        )
        QuestionResult.objects.create(
            task=previous_task,
            sample_id="toy-1",
            question_index=0,
            prompt_text="prompt",
            llm_response={"final_answer": "B"},
            llm_judge={"match": True},
            regex_judge=[{"matched": True}],
        )

        response = self.client.post(
            "/api/tasks/runs",
            data=json.dumps(
                {
                    "model_names": ["gpt-oss:20b"],
                    "dataset_names": ["toyset"],
                    "language_codes": ["en"],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["completed_tasks"], 1)
        benchmark_task = next(task for task in payload["tasks"] if task["task_kind"] == "benchmark")
        self.assertEqual(benchmark_task["status"], "completed")
        self.assertEqual(benchmark_task["completed_questions"], 1)
        self.assertEqual(QuestionResult.objects.count(), 2)

    def test_list_runs_includes_completed_history(self) -> None:
        first = BenchmarkRun.objects.create(
            language_code="en",
            provider_name="ollama",
            judge_provider="ollama",
            judge_model="gpt-oss:20b",
            translate_provider="ollama",
            translate_model="gpt-oss:20b",
            total_tasks=1,
            completed_tasks=1,
            status="completed",
        )
        first.tasks.create(
            status="completed",
            task_kind="benchmark",
            model_name="gpt-oss:20b",
            dataset_name="bbh",
            dataset_display_name="BBH",
            language_code="en",
            source_language="en",
            needs_translation=False,
            total_questions=250,
            completed_questions=250,
            progress_percent=100,
        )
        second = BenchmarkRun.objects.create(
            language_code="fr",
            provider_name="ollama",
            judge_provider="ollama",
            judge_model="gpt-oss:20b",
            translate_provider="ollama",
            translate_model="gpt-oss:20b",
            total_tasks=1,
            completed_tasks=0,
            status="pending",
        )
        second.tasks.create(
            status="pending",
            task_kind="translation",
            model_name="gpt-oss:20b",
            dataset_name="mmlu",
            dataset_display_name="MMLU",
            language_code="fr",
            source_language="en",
            needs_translation=True,
            total_questions=14042,
            completed_questions=0,
            progress_percent=0,
        )

        response = self.client.get("/api/tasks/runs")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        run_ids = {item["id"] for item in payload}
        self.assertIn(str(first.id), run_ids)
        self.assertIn(str(second.id), run_ids)
