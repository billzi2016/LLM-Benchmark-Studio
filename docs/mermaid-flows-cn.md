# LLM Benchmark Studio Mermaid 流程图

本文档用 Mermaid 展示 LLM Benchmark Studio 的主要产品流程和运行流程。

## 系统架构

```mermaid
flowchart LR
  User[用户浏览器] -->|http://localhost:6342| Vue[Vue Vite 前端]
  Vue -->|REST API| Django[Django Ninja API]
  Vue -->|后续 SSE| Django

  Django -->|SQL| PostgreSQL[(PostgreSQL)]
  Django -->|投递任务| RabbitMQ[(RabbitMQ)]
  Celery[Celery Worker] -->|消费任务| RabbitMQ
  Celery -->|读写结果| PostgreSQL

  Django -->|health + generate| Ollama[Ollama]
  Django -->|OpenAI compatible| OpenAI[OpenAI API]
  Django -->|OpenAI compatible| OpenRouter[OpenRouter]
  Django -->|OpenAI compatible| VLLM[vLLM]
  Django -->|OpenAI compatible| SGLang[SGLang]
  Django -->|OpenAI compatible| LocalAPI[本地 Transformers OpenAI API]

  RawData[data/benchmark_datasets/raw] --> Parser[data/parse_all_datasets.py]
  Parser --> JsonData[data/benchmark_datasets/*.json]
  Django -->|导入标准 JSON| PostgreSQL
```

## Docker Compose 启动流程

```mermaid
flowchart TD
  Start[docker compose up --build] --> PG[postgres service]
  Start --> MQ[rabbitmq service]

  PG -->|healthcheck ok| Backend[backend service]
  MQ -->|healthcheck ok| Backend
  Backend -->|python manage.py migrate| Migrate[自动执行 Django 迁移]
  Migrate --> Runserver[启动 Django 0.0.0.0:8000]
  Runserver --> HostAPI[宿主机端口 6341]

  Backend --> Frontend[frontend service]
  Frontend --> Pnpm[pnpm install --frozen-lockfile]
  Pnpm --> Vite[Vite dev server 0.0.0.0:5173]
  Vite --> HostUI[宿主机端口 6342]

  PG --> PGData[./.docker/postgres/data]
```

## 数据集下载与解析

```mermaid
flowchart TD
  Config[data/parser_json_rules.json] --> Download[data/download_default_datasets.py]
  Download --> Raw[data/benchmark_datasets/raw/*.jsonl]
  Config --> Parse[data/parse_all_datasets.py]
  Raw --> Parse
  Parse --> Normalize[标准化题目结构]
  Normalize --> Source[source 元信息]
  Normalize --> Questions[questions 数组]
  Questions --> Question[question.question_stem/options/answer]
  Questions --> EmptyResults[llm_response + llm_judge + regex_judge]
  Source --> Json[data/benchmark_datasets/*.json]
  EmptyResults --> Json
```

## Benchmark 队列创建

```mermaid
flowchart TD
  UI[Vue Studio] --> SelectModels[选择 active 模型]
  UI --> SelectDatasets[选择 benchmark 数据集]
  UI --> SelectLanguage[选择目标语言]

  SelectModels --> Queue[创建模型优先队列]
  SelectDatasets --> Queue
  SelectLanguage --> Queue

  Queue --> ModelA[模型 A 跑完所有选中数据集]
  ModelA --> ModelB[模型 B 跑完所有选中数据集]
  ModelB --> ModelC[模型 C 跑完所有选中数据集]

  ModelA --> TaskOrder[run_group_id -> model_group_order -> dataset_order -> sample_order]
```

## 单个测评任务

```mermaid
sequenceDiagram
  participant UI as Vue Task Queue
  participant API as Django Ninja API
  participant MQ as RabbitMQ
  participant Worker as Celery Worker
  participant DB as PostgreSQL
  participant LLM as 选中的 LLM Provider

  UI->>API: 创建单个 benchmark task
  API->>DB: 保存 pending 任务
  API->>MQ: 投递任务
  Worker->>MQ: 消费一个任务
  Worker->>DB: 读取数据集题目
  Worker->>LLM: prompt 包含题干、选项和严格输出规则
  LLM-->>Worker: 只返回最终答案
  Worker->>DB: 保存 llm_response[model_name]
  Worker->>DB: 标记任务完成
  UI->>API: 轮询或 SSE 获取进度
  API-->>UI: 返回任务状态
```

## LLM Provider 选择

```mermaid
flowchart LR
  Env[.env provider 设置] --> Registry[Provider registry]
  Registry --> Default[DEFAULT_PROVIDER]
  Registry --> Judge[JUDGE_PROVIDER + JUDGE_MODEL]
  Registry --> Translate[TRANSLATE_PROVIDER + TRANSLATE_MODEL]

  Default --> Ollama[ollama]
  Default --> OpenAICompatible[openai compatible]
  OpenAICompatible --> OpenAI[openai]
  OpenAICompatible --> OpenRouter[openrouter]
  OpenAICompatible --> VLLM[vllm]
  OpenAICompatible --> SGLang[sglang]
  OpenAICompatible --> Local[local-transformers-openai-api]

  ModelRegistry[data/llm_model_names.json] --> ContextRule{supports_think?}
  ContextRule -->|yes| ThinkCtx[LLM_CONTEXT_THINK 64k]
  ContextRule -->|no| DirectCtx[LLM_CONTEXT_NO_THINK 16k]
```

## LLM Judge 与 Regex Judge

```mermaid
flowchart TD
  Question[题干 + 选项 + 标准答案] --> JudgeContext[Judge prompt 上下文]
  Response[llm_response[model_name]] --> JudgeContext
  JudgeModel[JUDGE_MODEL] --> LLMJudge[LLM judge]
  JudgeContext --> LLMJudge
  LLMJudge --> SaveJudge[保存 llm_judge[model_name]]

  Response --> RegexRule[regex_judge_rule]
  RegexRule --> RegexJudge[Regex judge]
  RegexJudge --> SaveRegex[保存 regex_judge[model_name]]

  SaveJudge --> DB[(PostgreSQL)]
  SaveRegex --> DB
```

## 翻译流程

```mermaid
flowchart TD
  Dataset[数据集 source_language] --> Target[data/languages.json 目标语言]
  Target --> SameLanguage{是否与源语言相同?}
  SameLanguage -->|是| Skip[跳过翻译]
  SameLanguage -->|否| TranslateTask[创建翻译任务]
  TranslateTask --> TranslateProvider[TRANSLATE_PROVIDER]
  TranslateProvider --> TranslateModel[TRANSLATE_MODEL]
  TranslateModel --> TranslatedDataset[翻译后的标准数据集]
  TranslatedDataset --> DB[(PostgreSQL)]
```

## System Health 面板

```mermaid
flowchart TD
  Vue[System 面板] --> StatusAPI[GET /api/system/status]
  StatusAPI --> BackendHealth[Django API health]
  StatusAPI --> DBHealth[PostgreSQL SELECT 1]
  StatusAPI --> MQHealth[RabbitMQ TCP check]
  StatusAPI --> ProviderHealth[启用的 provider health]

  ProviderHealth --> OllamaTags[Ollama /api/tags]
  ProviderHealth --> OpenAIModels[OpenAI-compatible /models]

  BackendHealth --> Services[services 数组]
  DBHealth --> Services
  MQHealth --> Services
  ProviderHealth --> Services
  Services --> UI[ok / error / off 状态徽标]
```

## 结果导出

```mermaid
sequenceDiagram
  participant UI as Vue
  participant API as Django API
  participant DB as PostgreSQL
  participant ZIP as ZIP Builder

  UI->>API: 点击 Export
  API->>DB: 查询数据集、模型回答、judge、任务
  DB-->>API: 返回结果数据
  API->>ZIP: 打包压缩 JSON
  ZIP-->>API: ZIP stream
  API-->>UI: application/zip
  UI->>UI: 浏览器下载 results.zip
```

## 标准 JSON 结构

```mermaid
classDiagram
  class StudioDataset {
    source
    questions
  }

  class Source {
    dataset_name
    display_name
    source_language
    task_type
    benchmark_prompt
    judge_prompt
    regex_judge_rule
  }

  class QuestionRecord {
    sample_id
    language
    activate
    question
    llm_response
    llm_judge
    regex_judge
    metadata
  }

  class Question {
    question_stem
    options
    answer
  }

  StudioDataset --> Source
  StudioDataset --> QuestionRecord
  QuestionRecord --> Question
```
