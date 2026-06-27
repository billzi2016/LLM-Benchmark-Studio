# LLM Benchmark Studio Mermaid Flows

This document shows the main product and runtime flows for LLM Benchmark Studio.

## System Architecture

```mermaid
flowchart LR
  User[User Browser] -->|http://localhost:6342| Vue[Vue Vite Frontend]
  Vue -->|REST API| Django[Django Ninja API]
  Vue -->|SSE later| Django

  Django -->|SQL| PostgreSQL[(PostgreSQL)]
  Django -->|enqueue jobs| RabbitMQ[(RabbitMQ)]
  Celery[Celery Worker] -->|consume jobs| RabbitMQ
  Celery -->|read/write results| PostgreSQL

  Django -->|health + generate| Ollama[Ollama]
  Django -->|OpenAI compatible| OpenAI[OpenAI API]
  Django -->|OpenAI compatible| OpenRouter[OpenRouter]
  Django -->|OpenAI compatible| VLLM[vLLM]
  Django -->|OpenAI compatible| SGLang[SGLang]
  Django -->|OpenAI compatible| LocalAPI[Local Transformers OpenAI API]

  RawData[data/benchmark_datasets/raw] --> Parser[data/parse_all_datasets.py]
  Parser --> JsonData[data/benchmark_datasets/*.json]
  Django -->|import normalized JSON| PostgreSQL
```

## Docker Compose Startup

```mermaid
flowchart TD
  Start[docker compose up --build] --> PG[postgres service]
  Start --> MQ[rabbitmq service]

  PG -->|healthcheck ok| Backend[backend service]
  MQ -->|healthcheck ok| Backend
  Backend -->|python manage.py migrate| Migrate[Apply Django migrations]
  Migrate --> Runserver[Run Django on container port 8000]
  Runserver --> HostAPI[Host port 6341]

  Backend --> Frontend[frontend service]
  Frontend --> Pnpm[pnpm install --frozen-lockfile]
  Pnpm --> Vite[Vite dev server on container port 5173]
  Vite --> HostUI[Host port 6342]

  PG --> PGData[./.docker/postgres/data]
```

## Dataset Download And Parse

```mermaid
flowchart TD
  Config[data/parser_json_rules.json] --> Download[data/download_default_datasets.py]
  Download --> Raw[data/benchmark_datasets/raw/*.jsonl]
  Config --> Parse[data/parse_all_datasets.py]
  Raw --> Parse
  Parse --> Normalize[Normalize question shape]
  Normalize --> Source[source metadata]
  Normalize --> Questions[questions array]
  Questions --> Question[question.question_stem/options/answer]
  Questions --> EmptyResults[llm_response + llm_judge + regex_judge]
  Source --> Json[data/benchmark_datasets/*.json]
  EmptyResults --> Json
```

## Benchmark Queue Creation

```mermaid
flowchart TD
  UI[Vue Studio] --> SelectModels[Select active models]
  UI --> SelectDatasets[Select benchmark datasets]
  UI --> SelectLanguage[Select target language]

  SelectModels --> Queue[Create model-first queue]
  SelectDatasets --> Queue
  SelectLanguage --> Queue

  Queue --> ModelA[Model A: all selected datasets]
  ModelA --> ModelB[Model B: all selected datasets]
  ModelB --> ModelC[Model C: all selected datasets]

  ModelA --> TaskOrder[run_group_id -> model_group_order -> dataset_order -> sample_order]
```

## Single Benchmark Task

```mermaid
sequenceDiagram
  participant UI as Vue Task Queue
  participant API as Django Ninja API
  participant MQ as RabbitMQ
  participant Worker as Celery Worker
  participant DB as PostgreSQL
  participant LLM as Selected LLM Provider

  UI->>API: Create one benchmark task
  API->>DB: Save task pending
  API->>MQ: Enqueue task
  Worker->>MQ: Consume one task
  Worker->>DB: Load dataset question
  Worker->>LLM: Prompt with stem + options + strict output rule
  LLM-->>Worker: Final answer only
  Worker->>DB: Save llm_response[model_name]
  Worker->>DB: Mark task completed
  UI->>API: Poll/SSE progress
  API-->>UI: Updated task status
```

## LLM Provider Selection

```mermaid
flowchart LR
  Env[.env provider settings] --> Registry[Provider registry]
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

## Judge And Regex Judge

```mermaid
flowchart TD
  Question[question stem + options + gold answer] --> JudgeContext[Judge prompt context]
  Response[llm_response[model_name]] --> JudgeContext
  JudgeModel[JUDGE_MODEL] --> LLMJudge[LLM judge]
  JudgeContext --> LLMJudge
  LLMJudge --> SaveJudge[Save llm_judge[model_name]]

  Response --> RegexRule[regex_judge_rule]
  RegexRule --> RegexJudge[Regex judge]
  RegexJudge --> SaveRegex[Save regex_judge[model_name]]

  SaveJudge --> DB[(PostgreSQL)]
  SaveRegex --> DB
```

## Translation Flow

```mermaid
flowchart TD
  Dataset[Dataset source_language] --> Target[Target language from data/languages.json]
  Target --> SameLanguage{same as source?}
  SameLanguage -->|yes| Skip[Skip translation]
  SameLanguage -->|no| TranslateTask[Create translation task]
  TranslateTask --> TranslateProvider[TRANSLATE_PROVIDER]
  TranslateProvider --> TranslateModel[TRANSLATE_MODEL]
  TranslateModel --> TranslatedDataset[Translated normalized dataset]
  TranslatedDataset --> DB[(PostgreSQL)]
```

## System Health Panel

```mermaid
flowchart TD
  Vue[System panel] --> StatusAPI[GET /api/system/status]
  StatusAPI --> BackendHealth[Django API health]
  StatusAPI --> DBHealth[PostgreSQL SELECT 1]
  StatusAPI --> MQHealth[RabbitMQ TCP check]
  StatusAPI --> ProviderHealth[Enabled provider health]

  ProviderHealth --> OllamaTags[Ollama /api/tags]
  ProviderHealth --> OpenAIModels[OpenAI-compatible /models]

  BackendHealth --> Services[services array]
  DBHealth --> Services
  MQHealth --> Services
  ProviderHealth --> Services
  Services --> UI[ok / error / off badges]
```

## Result Export

```mermaid
sequenceDiagram
  participant UI as Vue
  participant API as Django API
  participant DB as PostgreSQL
  participant ZIP as ZIP Builder

  UI->>API: Click Export
  API->>DB: Query datasets, responses, judges, tasks
  DB-->>API: Result rows
  API->>ZIP: Build compressed JSON zip
  ZIP-->>API: zip stream
  API-->>UI: application/zip
  UI->>UI: Browser downloads results.zip
```

## Normalized JSON Shape

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
