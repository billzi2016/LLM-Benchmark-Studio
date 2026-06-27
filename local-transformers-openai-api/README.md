# Local Transformers OpenAI API

This directory contains a minimal self-hosted LLM server for local Transformers models and optional LoRA adapters.

The name is intentionally `local-transformers-openai-api`:

- `local`: runs on your own machine.
- `transformers`: loads Hugging Face Transformers models.
- `openai-api`: exposes an OpenAI-compatible `/v1/chat/completions` API.

It is not named `self-host-sft-llms` because the server can host base models, instruction models, SFT models, LoRA adapters, and other local transformer checkpoints.

Default port:

```text
6328
```

Backend provider config:

```env
OPENAI_COMPATIBLE_ENABLED=true
OPENAI_COMPATIBLE_HOST=localhost
OPENAI_COMPATIBLE_PORT=6328
OPENAI_COMPATIBLE_BASE_URL=http://localhost:6328/v1
OPENAI_COMPATIBLE_API_KEY=
```

Run:

```bash
python local-transformers-openai-api/openai_api_server.py \
  --model Qwen/Qwen2.5-0.5B-Instruct \
  --host 127.0.0.1 \
  --port 6328
```

Run with LoRA:

```bash
python local-transformers-openai-api/openai_api_server.py \
  --model /path/to/base-model \
  --lora /path/to/lora-adapter \
  --host 127.0.0.1 \
  --port 6328
```

Run from a multi-model registry:

```bash
python local-transformers-openai-api/openai_api_server.py \
  --registry local-transformers-openai-api/model_registry.example.json \
  --model-id qwen2_5_7b_lora_math \
  --host 127.0.0.1 \
  --port 6328
```

The registry can contain many base models and LoRA adapters, but one server process loads exactly one selected model. Start another process on another port if you want another model loaded at the same time.

Registry fields:

- `id`: internal selector used by `--model-id`.
- `served_model_name`: model name exposed by `/v1/models`.
- `base_model`: Hugging Face model id or local checkpoint path.
- `lora_adapter`: optional LoRA adapter path.
- `activate`: inactive models cannot be loaded.
- `device_map`: usually `auto`.
- `torch_dtype`: usually `auto`, `float16`, or `bfloat16`.

OpenAI-compatible endpoint:

```text
GET  /v1/models
POST /v1/chat/completions
```
