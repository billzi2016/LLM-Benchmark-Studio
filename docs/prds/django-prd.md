# Django PRD - LLM Benchmark Studio Backend

## 1. 目标

Django 后端只负责 API、鉴权预留、任务编排入口、SSE 事件推送、数据读写和 provider 调用封装。实际长任务由 Celery 执行，消息队列使用 RabbitMQ，所有测评结果和任务状态保存到 PostgreSQL。

后端必须是正式项目结构，根目录为 `backend/`，API 使用 Django Ninja，实时进度使用 Server-Sent Events。

## 2. 职责边界

Django 负责：

- 暴露 REST API 和 SSE API。
- 读取 `.env` 中的系统配置、provider 配置、模型配置和任务参数。
- 读取 `data/llm_model_names.json`，展示可用 LLM、是否支持 think、是否 activate。
- 读取 `data/languages.json`，展示目标翻译语言。
- 扫描 `data/benchmark_datasets/` 下的 JSON benchmark 数据集。
- 将 dataset、sample、language、model、response、judge、regex judge、task 状态保存到 PostgreSQL。
- 提交单个任务到 Celery 队列。
- 通过 SSE 推送任务进度、日志和状态变化。

Django 不负责：

- 不直接执行长时间 benchmark、translate、judge 任务。
- 不在 API 请求线程里批量调用 LLM。
- 不把测评结果只保存在 JSON 文件里，PostgreSQL 是主存储。

## 2.1 工程原则

后端必须遵守 DRY 和 SOLID：

- DRY：provider 调用、prompt 构造、answer normalization、task 状态更新、错误响应不能在多个 API 或 Celery task 中重复实现。
- Single Responsibility：API router 只做请求校验和调用 service，业务逻辑放 service，数据结构放 model/schema，长任务放 Celery runner。
- Open/Closed：新增 provider 时通过 provider registry 扩展，不修改 benchmark runner 主流程。
- Liskov Substitution：所有 provider 必须实现同一个接口，runner 不关心具体 provider 类型。
- Interface Segregation：benchmark、judge、translate 拆成独立 service，不做一个万能大 service。
- Dependency Inversion：业务流程依赖抽象 provider interface，不直接依赖 Ollama/OpenAI/OpenRouter SDK 细节。

原则上不自己造轮子。优先使用成熟 Django 生态套件：

- API：Django Ninja。
- 配置：django-environ 或 pydantic-settings。
- PostgreSQL：Django ORM + migrations。
- CORS：django-cors-headers。
- Celery 结果集成：django-celery-results。
- Celery 定时任务预留：django-celery-beat。
- 过滤和分页：django-filter 或 Ninja pagination。
- 测试：pytest-django。
- OpenAPI schema：Django Ninja 内置能力。

只有在成熟套件无法满足项目边界时，才允许实现轻量自定义代码。

## 2.2 安全要求

后端默认开启安全防护：

- CSRF：对 cookie/session 认证接口启用 Django CSRF middleware；纯 token API 必须明确标记豁免范围，不能全局关闭。
- CORS：使用 `django-cors-headers`，只允许 `.env` 中配置的前端 origin。
- XSS：后端不返回未经标记的 HTML；用户输入、dataset 内容、LLM 输出全部按纯文本或 JSON 返回。
- Security headers：启用 `SECURE_CONTENT_TYPE_NOSNIFF`、`X_FRAME_OPTIONS`、合理的 `Referrer-Policy`。
- CSP：生产环境通过 Django 或反向代理配置 Content Security Policy。
- 输入校验：所有 API request body 使用 Ninja schema 校验。
- 文件路径：dataset path 必须限制在 `data/benchmark_datasets/` 下，禁止任意路径读取。
- Provider secrets：API key 只从 `.env` 读取，永不返回给前端。
- 日志脱敏：provider call log 不记录 API key、Authorization header。

## 3. 核心功能

### 3.1 系统信息 API

接口返回前端第一列需要展示的 system 信息：

- Django 服务状态。
- PostgreSQL 连接状态。
- RabbitMQ 连接状态。
- Celery worker 状态。
- 当前默认 provider。
- 当前 judge provider 和 judge model。
- 当前 translate provider 和 translate model。
- 支持 think 模型上下文长度。
- 不支持 think 模型上下文长度。
- 数据集目录。
- 当前激活 dataset、model、language 数量。

### 3.2 模型 API

从 `data/llm_model_names.json` 载入模型，例如：

```json
[
  {
    "name": "gpt-oss:20b",
    "provider": "ollama",
    "supports_think": true,
    "context_length": 65536,
    "activate": true
  }
]
```

规则：

- `activate=false` 的模型默认不参与任务创建。
- `supports_think=true` 默认上下文长度使用 `.env` 中的 `LLM_CONTEXT_THINK=65536`。
- `supports_think=false` 默认上下文长度使用 `.env` 中的 `LLM_CONTEXT_NO_THINK=16384`。
- 模型名称可由 `ollama list` 初始化写入该 JSON，但后端只读取文件，不直接假设当前机器状态。

### 3.3 Dataset API

扫描目录：

```text
data/benchmark_datasets/
```

默认数据集文件格式为 JSON。每个 dataset 导入 PostgreSQL 时必须拆成结构化记录，而不是后期补丁式追加字段。

建议优先支持综合评估数据集：

- MMLU
- MMLU-Pro
- ARC-Challenge
- HellaSwag
- TruthfulQA
- GSM8K
- BBH
- Winogrande
- OpenBookQA

每个 dataset 文件建议规范：

```json
{
  "dataset_name": "mmlu",
  "subset": "abstract_algebra",
  "source_language": "en",
  "activate": true,
  "samples": [
    {
      "sample_id": "mmlu-abstract_algebra-000001",
      "question": "...",
      "choices": {
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
      },
      "answer": "A",
      "language": "en",
      "metadata": {}
    }
  ]
}
```

导入 PostgreSQL 后，LLM response、judge 和 regex judge 不直接回写原始 dataset 文件，而是保存到结果表。API 可按 JSON 结构返回组合结果。

### 3.4 Benchmark 执行 API

前端选择一个 dataset、一个 sample 或一个 dataset 中的下一个 sample、一个 LLM 后，创建单个任务：

- 一次只执行一个任务。
- 不做 batch。
- 避免 API 限流、Ollama 单并发阻塞、provider 崩溃。
- 每个任务由 Celery worker 消费。
- 如果用户选择多个模型和多个数据集，Django 创建任务时必须按模型分组排序：同一个模型的所有 dataset/sample 任务排在一起，再进入下一个模型。
- 任务排序字段写入 PostgreSQL，供 Celery 和 Vue 共同使用。

Prompt 规则：

- 将原始题目、选项、语言、原始答案格式要求一起打包到上下文。
- 对选择题要求只输出 `A`、`B`、`C`、`D` 等合法选项。
- 不允许输出解释。
- 支持 think 的模型可以使用 think 能力，但后端只保存最终答案，不保存 think。

### 3.5 Judge API

Judge 使用 `.env` 指定：

```env
JUDGE_PROVIDER=ollama
JUDGE_MODEL=gpt-oss:20b
```

Judge 输入必须包含：

- 原始题目。
- 选项。
- 标准答案。
- LLM 原始最终回答。
- 数据集语言。
- 评分规则。

Judge 输出保存到 `llm_judge` 结构字段：

```json
{
  "judge_provider": "ollama",
  "judge_model": "gpt-oss:20b",
  "match": true,
  "normalized_answer": "A",
  "reason": "The model selected A, which matches the gold answer.",
  "created_at": "..."
}
```

### 3.6 Regex Judge API

Regex judge 用于正则判断已有 response。结果保存到独立 `regex_judge` 字段，不覆盖原始 judge。

```json
{
  "judge_provider": "ollama",
  "judge_model": "gpt-oss:20b",
  "match": true,
  "normalized_answer": "A",
  "reason": "...",
  "created_at": "..."
}
```

### 3.7 Translation API

翻译语言从：

```text
data/languages.json
```

读取。示例：

```json
[
  {
    "code": "fr",
    "name": "French",
    "activate": true
  }
]
```

规则：

- 原始语言等于目标语言时不翻译。
- 保存到 PostgreSQL 时必须有 `language` 字段。
- 翻译任务也是单个 Celery 任务。
- 默认翻译模型：

```env
TRANSLATE_PROVIDER=ollama
TRANSLATE_MODEL=gpt-oss:20b
```

### 3.8 Results Export API

后端必须提供结果导出 API，供 Vue 一键下载全部结果。

规则：

- API 由 Django 负责查询 PostgreSQL 并生成 ZIP。
- ZIP 必须使用压缩。
- ZIP 内保存 JSON 文件。
- 默认导出全部 benchmark results。
- 后续可按 dataset、model、language、status、created_at 过滤。
- 导出内容必须包含 sample、dataset、language、model、provider、prompt、final answer、raw response、judge、regex judge、task metadata。
- 大结果导出应使用 streaming response 或临时文件，避免一次性占用过多内存。
- ZIP 文件名包含导出时间，例如 `llm-benchmark-results-20260627-153000.zip`。

## 4. API 草案

```text
GET  /api/system/status
GET  /api/models
GET  /api/datasets
GET  /api/languages
GET  /api/tasks
POST /api/tasks/benchmark
POST /api/tasks/judge
POST /api/tasks/regex judge
POST /api/tasks/translate
POST /api/tasks/{task_id}/play
POST /api/tasks/{task_id}/pause
POST /api/tasks/{task_id}/stop
GET  /api/tasks/{task_id}
GET  /api/events/tasks
GET  /api/results
GET  /api/results/{result_id}
GET  /api/results/export
```

## 5. Provider 抽象

后端需要统一封装以下 provider：

- Ollama
- OpenRouter
- OpenAI API
- vLLM OpenAI-compatible endpoint
- SGLang OpenAI-compatible endpoint

统一接口：

```python
class LLMProvider:
    def generate(self, model: str, messages: list[dict], temperature: float, max_tokens: int) -> LLMResponse:
        ...
```

返回对象必须区分：

- `raw_text`
- `final_answer`
- `thinking_text`，默认不入库。
- `usage`
- `latency_ms`
- `provider_metadata`

## 6. Project Tree

```text
backend/
  manage.py
  pyproject.toml
  README.md
  config/
    __init__.py
    settings/
      __init__.py
      base.py
      local.py
      production.py
    urls.py
    asgi.py
    wsgi.py
    celery.py
  apps/
    core/
      __init__.py
      env.py
      health.py
      schemas.py
    api/
      __init__.py
      router.py
      system.py
      models.py
      datasets.py
      languages.py
      tasks.py
      results.py
      exports.py
      events.py
    benchmarks/
      __init__.py
      models.py
      services/
        dataset_loader.py
        dataset_importer.py
        prompt_builder.py
        answer_normalizer.py
      schemas.py
      admin.py
    llms/
      __init__.py
      models.py
      providers/
        base.py
        ollama.py
        openai.py
        openrouter.py
        vllm.py
        sglang.py
      services/
        registry.py
        model_loader.py
        generation.py
    evaluations/
      __init__.py
      models.py
      services/
        benchmark_runner.py
        judge_runner.py
        translate_runner.py
        result_exporter.py
    taskqueue/
      __init__.py
      models.py
      tasks.py
      services/
        task_control.py
        progress.py
        sse.py
  tests/
    test_api_system.py
    test_dataset_importer.py
    test_prompt_builder.py
    test_answer_normalizer.py
    test_task_creation.py
```

## 7. 验收标准

- Django 项目可以独立启动 API。
- Ninja 自动生成 API schema。
- SSE 能推送 task 状态。
- API 不在请求线程执行长任务。
- 所有结果写入 PostgreSQL。
- `.env` 中的 provider、模型、上下文长度、任务参数能被 API 展示。
- `activate=false` 的模型、语言、dataset 不进入默认任务候选。
