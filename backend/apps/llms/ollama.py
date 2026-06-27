from __future__ import annotations

from typing import Any

import requests


class OllamaClient:
    provider = "ollama"

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        models = payload.get("models", [])
        return {
            "status": "ok",
            "base_url": self.base_url,
            "model_count": len(models),
            "models": [
                {
                    "name": model.get("name"),
                    "size": model.get("size"),
                    "modified_at": model.get("modified_at"),
                }
                for model in models
            ],
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
            "stream": False,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        message = data.get("message") or {}
        final_answer = str(message.get("content") or data.get("response") or "").strip()
        return {
            "provider": "ollama",
            "model": model,
            "raw_response": final_answer,
            "final_answer": final_answer,
            "thinking_present": bool(message.get("thinking") or data.get("thinking")),
            "done": data.get("done"),
            "done_reason": data.get("done_reason"),
            "usage": {
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
                "total_duration": data.get("total_duration"),
            },
        }
