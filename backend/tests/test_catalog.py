from __future__ import annotations

from django.conf import settings
from django.test import SimpleTestCase

from apps.datasets.catalog import load_dataset, safe_dataset_path, scan_datasets
from apps.datasets.languages import load_languages
from apps.llms.registry import load_model_registry


class CatalogTests(SimpleTestCase):
    def test_scan_datasets_reads_normalized_json(self) -> None:
        datasets = scan_datasets(settings.BENCHMARK_DATASETS_DIR)
        names = {dataset["dataset_name"] for dataset in datasets}
        self.assertIn("mmlu", names)
        self.assertIn("mmlu_pro", names)
        self.assertTrue(all(dataset["question_count"] > 0 for dataset in datasets))

    def test_load_dataset_keeps_expected_question_shape(self) -> None:
        dataset = load_dataset(settings.BENCHMARK_DATASETS_DIR, "mmlu")
        first_question = dataset["questions"][0]
        self.assertIn("source", dataset)
        self.assertIn("question_stem", first_question["question"])
        self.assertIn("options", first_question["question"])
        self.assertIn("answer", first_question["question"])
        self.assertEqual(first_question["llm_response"], {})
        self.assertEqual(first_question["llm_judge"], {})
        self.assertEqual(first_question["regex_judge"], [])

    def test_safe_dataset_path_rejects_path_traversal(self) -> None:
        with self.assertRaises(ValueError):
            safe_dataset_path(settings.BENCHMARK_DATASETS_DIR, "../secrets")

    def test_load_model_registry(self) -> None:
        models = load_model_registry(settings.LLM_MODEL_NAMES_PATH)
        self.assertTrue(models)
        self.assertTrue(any(model["name"] == "gpt-oss:20b" for model in models))

    def test_load_languages(self) -> None:
        languages = load_languages(settings.LANGUAGES_PATH)
        self.assertTrue(languages)
        self.assertTrue(any(language["code"] == "en" for language in languages))
