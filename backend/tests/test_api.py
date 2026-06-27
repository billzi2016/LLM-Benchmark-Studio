from __future__ import annotations

from django.test import Client, SimpleTestCase


class ApiTests(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_system_status(self) -> None:
        response = self.client.get("/api/system/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["service"], "django")

    def test_models(self) -> None:
        response = self.client.get("/api/models")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertGreater(payload["meta"]["total"], 0)

    def test_llm_providers(self) -> None:
        response = self.client.get("/api/llms/providers")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        provider_names = {provider["provider"] for provider in payload["data"]}
        self.assertIn("ollama", provider_names)
        self.assertIn("openai_compatible", provider_names)
        self.assertTrue(all("api_key" not in provider for provider in payload["data"]))
        self.assertTrue(all("api_key_configured" in provider for provider in payload["data"]))

    def test_languages(self) -> None:
        response = self.client.get("/api/languages")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertGreater(payload["meta"]["total"], 0)

    def test_datasets(self) -> None:
        response = self.client.get("/api/datasets")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(any(dataset["dataset_name"] == "mmlu" for dataset in payload["data"]))

    def test_dataset_detail_without_questions_by_default(self) -> None:
        response = self.client.get("/api/datasets/mmlu")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["questions"], [])

    def test_dataset_detail_with_questions(self) -> None:
        response = self.client.get("/api/datasets/mmlu?include_questions=true")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["data"]["questions"])
