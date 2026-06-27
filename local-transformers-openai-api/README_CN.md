# Local Transformers OpenAI API 中文说明

这个目录用于把本地 Hugging Face Transformers 模型包装成 OpenAI-compatible API。

它适合这些场景：

- 直接加载一个本地 base model。
- 加载一个 base model + LoRA adapter。
- 一个 registry 里配置多个模型和 LoRA，但每次服务进程只 load 一个。
- 给主项目 Django provider 使用 `openai_compatible` 方式调用。

目录名使用 `local-transformers-openai-api`，不是 `self-host-sft-llms`，原因是这里不只支持 SFT 模型，也支持 base model、instruction model、LoRA adapter 和其他本地 transformer checkpoint。

## 端口

默认端口：

```text
6328
```

主项目 `.env` 对应配置：

```env
OPENAI_COMPATIBLE_ENABLED=true
OPENAI_COMPATIBLE_HOST=localhost
OPENAI_COMPATIBLE_PORT=6328
OPENAI_COMPATIBLE_BASE_URL=http://localhost:6328/v1
OPENAI_COMPATIBLE_API_KEY=
```

## 安装依赖

在项目根目录安装：

```bash
pip install -r requirements.txt
```

依赖包含：

- fastapi
- uvicorn
- transformers
- accelerate
- peft
- torch

## 直接加载一个模型

```bash
python local-transformers-openai-api/openai_api_server.py \
  --model Qwen/Qwen2.5-0.5B-Instruct \
  --host 127.0.0.1 \
  --port 6328
```

## 加载 base model + LoRA

```bash
python local-transformers-openai-api/openai_api_server.py \
  --model /path/to/base-model \
  --lora /path/to/lora-adapter \
  --host 127.0.0.1 \
  --port 6328
```

## 使用多模型 registry

registry 文件示例：

```text
local-transformers-openai-api/model_registry.example.json
```

启动其中一个模型：

```bash
python local-transformers-openai-api/openai_api_server.py \
  --registry local-transformers-openai-api/model_registry.example.json \
  --model-id qwen2_5_7b_lora_math \
  --host 127.0.0.1 \
  --port 6328
```

注意：registry 可以配置很多模型，但一个进程一次只 load 一个模型。这样做是为了避免显存和内存被多个模型同时占满，也避免 HDD 环境频繁加载多个模型导致很慢。

如果要同时提供多个模型，需要启动多个进程，并给每个进程不同端口。

## Registry 字段

```json
{
  "id": "qwen2_5_7b_lora_math",
  "served_model_name": "qwen2.5-7b-lora-math",
  "base_model": "/models/Qwen2.5-7B-Instruct",
  "lora_adapter": "/loras/qwen2.5-7b-math-lora",
  "activate": true,
  "device_map": "auto",
  "torch_dtype": "auto"
}
```

字段说明：

- `id`：启动时传给 `--model-id` 的内部名称。
- `served_model_name`：对外暴露给 `/v1/models` 的模型名。
- `base_model`：Hugging Face 模型名或本地 checkpoint 路径。
- `lora_adapter`：LoRA adapter 路径；没有 LoRA 时填 `null`。
- `activate`：为 `false` 时禁止加载。
- `device_map`：通常使用 `auto`。
- `torch_dtype`：通常使用 `auto`、`float16` 或 `bfloat16`。

## OpenAI-Compatible 接口

列出模型：

```text
GET /v1/models
```

聊天生成：

```text
POST /v1/chat/completions
```

请求示例：

```bash
curl http://localhost:6328/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-7b-lora-math",
    "messages": [
      {"role": "user", "content": "Answer only A, B, C, or D. 1+1=? A.1 B.2 C.3 D.4"}
    ],
    "temperature": 0,
    "max_tokens": 32,
    "stream": false
  }'
```

当前最小服务暂不支持 stream。

## 和主项目联动

启动本地服务后，主项目 Django 可以用 `openai_compatible` provider 调用：

```text
GET  /api/llms/openai_compatible/health
POST /api/llms/openai_compatible/generate
```

如果你把本地服务改到别的 IP 或端口，只需要改 `.env`：

```env
OPENAI_COMPATIBLE_HOST=192.168.1.20
OPENAI_COMPATIBLE_PORT=9000
OPENAI_COMPATIBLE_BASE_URL=http://192.168.1.20:9000/v1
```
