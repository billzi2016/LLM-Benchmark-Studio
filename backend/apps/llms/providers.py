from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import requests

from apps.llms.ollama import OllamaClient


class LLMProvider(Protocol):
    provider: str

    def health(self) -> dict[str, Any]:
        ...

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 128,
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    protocol: str
    base_url: str
    api_key: str
    timeout: float
    enabled: bool

    @classmethod
    def from_mapping(cls, config: dict[str, Any]) -> "ProviderConfig":
        return cls(
            provider=str(config["provider"]),
            protocol=str(config["protocol"]),
            base_url=str(config["base_url"]).rstrip("/"),
            api_key=str(config.get("api_key") or ""),
            timeout=float(config.get("timeout") or 120),
            enabled=bool(config.get("enabled")),
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "protocol": self.protocol,
            "base_url": self.base_url,
            "enabled": self.enabled,
            "api_key_configured": bool(self.api_key),
        }


class OpenAICompatibleClient:
    def __init__(self, config: ProviderConfig) -> None:
        self.provider = config.provider
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key
        self.timeout = config.timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "http://localhost:6325"
            headers["X-Title"] = "LLM Benchmark Studio"
        return headers

    def health(self) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/models",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        models = payload.get("data", [])
        return {
            "status": "ok",
            "provider": self.provider,
            "protocol": "openai_compatible",
            "base_url": self.base_url,
            "model_count": len(models) if isinstance(models, list) else None,
            "models": models if isinstance(models, list) else [],
        }

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 128,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        content = str(message.get("content") or "").strip()
        return {
            "provider": self.provider,
            "model": model,
            "raw_response": content,
            "final_answer": content,
            "thinking_present": False,
            "done": True,
            "done_reason": choices[0].get("finish_reason") if choices else None,
            "usage": data.get("usage") or {},
        }


def sanitize_provider_configs(provider_configs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        ProviderConfig.from_mapping(config).public_dict()
        for _, config in sorted(provider_configs.items())
    ]


def get_provider(provider_name: str, provider_configs: dict[str, dict[str, Any]]) -> LLMProvider:
    if provider_name not in provider_configs:
        raise ValueError(f"Unknown provider: {provider_name}")
    config = ProviderConfig.from_mapping(provider_configs[provider_name])
    if config.protocol == "ollama":
        client = OllamaClient(config.base_url, timeout=config.timeout)
        client.provider = config.provider
        return client
    if config.protocol == "openai_compatible":
        return OpenAICompatibleClient(config)
    raise ValueError(f"Unsupported provider protocol: {config.protocol}")
