from __future__ import annotations

from unittest.mock import Mock, patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from apps.llms.providers import OpenAICompatibleClient, ProviderConfig, get_provider, sanitize_provider_configs


class ProviderRegistryTests(SimpleTestCase):
    def test_sanitize_provider_configs_does_not_expose_api_key(self) -> None:
        configs = {
            "openai_compatible": {
                "provider": "openai_compatible",
                "protocol": "openai_compatible",
                "base_url": "http://127.0.0.1:6328/v1",
                "api_key": "secret",
                "timeout": 10,
                "enabled": True,
            }
        }

        public = sanitize_provider_configs(configs)

        self.assertEqual(public[0]["provider"], "openai_compatible")
        self.assertTrue(public[0]["api_key_configured"])
        self.assertNotIn("secret", str(public))

    def test_get_provider_supports_ollama(self) -> None:
        provider = get_provider("ollama", settings.LLM_PROVIDERS)
        self.assertEqual(provider.provider, "ollama")

    @override_settings(
        LLM_PROVIDERS={
            "openai_compatible": {
                "provider": "openai_compatible",
                "protocol": "openai_compatible",
                "base_url": "http://127.0.0.1:6328/v1",
                "api_key": "",
                "timeout": 10,
                "enabled": True,
            }
        }
    )
    def test_get_provider_supports_openai_compatible(self) -> None:
        provider = get_provider("openai_compatible", settings.LLM_PROVIDERS)
        self.assertEqual(provider.provider, "openai_compatible")


class OpenAICompatibleClientTests(SimpleTestCase):
    def build_client(self) -> OpenAICompatibleClient:
        return OpenAICompatibleClient(
            ProviderConfig(
                provider="openai_compatible",
                protocol="openai_compatible",
                base_url="http://127.0.0.1:6328/v1",
                api_key="test-key",
                timeout=10,
                enabled=True,
            )
        )

    @patch("apps.llms.providers.requests.get")
    def test_health_uses_models_endpoint(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.json.return_value = {"data": [{"id": "local-model"}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.build_client().health()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["model_count"], 1)
        mock_get.assert_called_once()
        self.assertTrue(mock_get.call_args.kwargs["headers"]["Authorization"].startswith("Bearer "))

    @patch("apps.llms.providers.requests.post")
    def test_generate_uses_chat_completions_endpoint(self, mock_post: Mock) -> None:
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "A"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 1},
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.build_client().generate("local-model", "Return A")

        self.assertEqual(result["provider"], "openai_compatible")
        self.assertEqual(result["final_answer"], "A")
        self.assertFalse(result["thinking_present"])
        self.assertTrue(mock_post.call_args.args[0].endswith("/chat/completions"))
