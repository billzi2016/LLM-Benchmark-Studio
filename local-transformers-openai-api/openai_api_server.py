from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from transformers_model import GenerationConfig, LocalTransformerModel


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.0
    max_tokens: int = Field(default=128, alias="max_tokens")
    stream: bool = False


def create_app(model: LocalTransformerModel, served_model_name: str) -> FastAPI:
    app = FastAPI(title="Local Transformers OpenAI-Compatible API")

    @app.get("/v1/models")
    def list_models() -> dict:
        return {
            "object": "list",
            "data": [
                {
                    "id": served_model_name,
                    "object": "model",
                    "created": 0,
                    "owned_by": "local",
                }
            ],
        }

    @app.post("/v1/chat/completions")
    def chat_completions(request: ChatCompletionRequest) -> dict:
        if request.stream:
            raise ValueError("Streaming is not supported in this minimal server yet.")
        result = model.chat(
            [message.model_dump() for message in request.messages],
            GenerationConfig(
                temperature=request.temperature,
                max_new_tokens=request.max_tokens,
                do_sample=request.temperature > 0,
            ),
        )
        created = int(time.time())
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": created,
            "model": served_model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result["content"],
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
                "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
            },
        }

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a local Transformers model as OpenAI-compatible API.")
    parser.add_argument("--registry", default=None, help="Optional model registry JSON.")
    parser.add_argument("--model-id", default=None, help="Model id to load from registry. Only one model is loaded.")
    parser.add_argument("--model", default=None, help="Base model name or local path.")
    parser.add_argument("--lora", default=None, help="Optional LoRA adapter path.")
    parser.add_argument("--served-model-name", default=None, help="Model id exposed by /v1/models.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6328)
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--torch-dtype", default="auto")
    return parser.parse_args()


def resolve_model_config(args: argparse.Namespace) -> dict:
    if args.registry:
        registry_path = Path(args.registry)
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        models = registry.get("models", [])
        if not args.model_id:
            raise ValueError("--model-id is required when --registry is used.")
        matches = [model for model in models if model.get("id") == args.model_id]
        if not matches:
            raise ValueError(f"Model id not found in registry: {args.model_id}")
        selected = matches[0]
        if not selected.get("activate", True):
            raise ValueError(f"Model is not active in registry: {args.model_id}")
        return {
            "model": selected["base_model"],
            "lora": selected.get("lora_adapter"),
            "served_model_name": selected.get("served_model_name") or selected["id"],
            "device_map": selected.get("device_map") or args.device_map,
            "torch_dtype": selected.get("torch_dtype") or args.torch_dtype,
        }

    if not args.model:
        raise ValueError("Either --model or --registry + --model-id is required.")
    return {
        "model": args.model,
        "lora": args.lora,
        "served_model_name": args.served_model_name or args.model,
        "device_map": args.device_map,
        "torch_dtype": args.torch_dtype,
    }


def main() -> None:
    args = parse_args()
    selected = resolve_model_config(args)
    model = LocalTransformerModel(
        model_name_or_path=selected["model"],
        lora_path=selected["lora"],
        device_map=selected["device_map"],
        torch_dtype=selected["torch_dtype"],
    )
    app = create_app(model, selected["served_model_name"])
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
