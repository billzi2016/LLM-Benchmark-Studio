from __future__ import annotations

from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.llms.ollama import OllamaClient


class OllamaClientTests(SimpleTestCase):
    @patch("apps.llms.ollama.requests.get")
    def test_health(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.json.return_value = {"models": [{"name": "gpt-oss:20b", "size": 123}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        health = OllamaClient("http://127.0.0.1:11434").health()

        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["model_count"], 1)
        self.assertEqual(health["models"][0]["name"], "gpt-oss:20b")

    @patch("apps.llms.ollama.requests.post")
    def test_generate(self, mock_post: Mock) -> None:
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "A\n",
                "thinking": "hidden reasoning",
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 10,
            "eval_count": 1,
            "total_duration": 100,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = OllamaClient("http://127.0.0.1:11434").generate(
            model="gpt-oss:20b",
            prompt="Return only A.",
        )

        self.assertEqual(result["raw_response"], "A")
        self.assertEqual(result["final_answer"], "A")
        self.assertTrue(result["thinking_present"])
        self.assertNotIn("hidden reasoning", str(result))
