# PostgreSQL PRD - LLM Benchmark Studio Storage

## 1. 目标

PostgreSQL 是 LLM Benchmark Studio 的主存储。所有 dataset 元数据、sample、翻译、LLM response、judge、regex judge、任务状态和 provider 调用记录都保存到 PostgreSQL。

设计原则是一次性建立完整数据表，不做一个字段一个字段的补丁式演进。

## 2. 数据原则

- 原始 dataset JSON 作为导入源。
- PostgreSQL 作为业务主存储。
- 每个 sample 必须有语言字段。
- 每个可选实体必须有 `activate` 字段。
- LLM response、judge、regex judge 必须支持多模型、多 provider、多轮运行。
- 不保存 think 内容，只保存最终答案和必要 metadata。
- Prompt、原始题目、选项、标准答案、模型输出、judge 结果要可追溯。

## 3. 核心实体

### 3.1 datasets

保存 benchmark dataset 元数据。

字段：

- `id`
- `name`
- `subset`
- `description`
- `source_path`
- `source_language`
- `sample_count`
- `activate`
- `metadata`
- `created_at`
- `updated_at`

唯一约束：

- `(name, subset, source_language)`

### 3.2 benchmark_samples

保存题目样本。

字段：

- `id`
- `dataset_id`
- `external_id`
- `question`
- `choices`
- `gold_answer`
- `answer_format`
- `language`
- `difficulty`
- `category`
- `metadata`
- `activate`
- `created_at`
- `updated_at`

`choices` 使用 JSONB：

```json
{
  "A": "...",
  "B": "...",
  "C": "...",
  "D": "..."
}
```

### 3.3 languages

保存可选翻译语言。

字段：

- `id`
- `code`
- `name`
- `native_name`
- `activate`
- `metadata`
- `created_at`
- `updated_at`

### 3.4 llm_models

保存模型配置快照。

字段：

- `id`
- `name`
- `provider`
- `supports_think`
- `context_length`
- `activate`
- `source`
- `metadata`
- `created_at`
- `updated_at`

### 3.5 benchmark_runs

保存一次 benchmark 运行。

字段：

- `id`
- `sample_id`
- `model_id`
- `provider`
- `model_name`
- `prompt`
- `raw_response`
- `final_answer`
- `normalized_answer`
- `usage`
- `latency_ms`
- `status`
- `error_message`
- `metadata`
- `created_at`
- `updated_at`

注意：

- `raw_response` 保存模型原始最终输出。
- 如果 provider 返回 think 内容，不保存 think。
- `final_answer` 是抽取后的最终答案。
- `normalized_answer` 是归一化后的答案，例如 `A`。

### 3.6 judge_results

保存首次 judge 结果。

字段：

- `id`
- `benchmark_run_id`
- `judge_provider`
- `judge_model`
- `judge_prompt`
- `judge_raw_response`
- `match`
- `normalized_gold_answer`
- `normalized_model_answer`
- `score`
- `reason`
- `metadata`
- `created_at`
- `updated_at`

### 3.7 regex_judge_results

保存 regex judge 结果，不覆盖首次 judge。

字段：

- `id`
- `benchmark_run_id`
- `judge_provider`
- `judge_model`
- `judge_prompt`
- `judge_raw_response`
- `match`
- `normalized_gold_answer`
- `normalized_model_answer`
- `score`
- `reason`
- `metadata`
- `created_at`
- `updated_at`

### 3.8 translations

保存翻译后的 sample。

字段：

- `id`
- `source_sample_id`
- `target_language`
- `translator_provider`
- `translator_model`
- `translated_question`
- `translated_choices`
- `translated_gold_answer`
- `status`
- `error_message`
- `metadata`
- `created_at`
- `updated_at`

规则：

- 如果 `source_sample.language == target_language`，不创建翻译记录。
- 翻译后的 sample 可以作为 benchmark 输入，但必须保留 `source_sample_id`。

### 3.9 task_queue

保存任务队列状态。

字段：

- `id`
- `celery_task_id`
- `task_type`
- `status`
- `priority`
- `dataset_id`
- `sample_id`
- `model_id`
- `benchmark_run_id`
- `target_language`
- `progress_current`
- `progress_total`
- `progress_percent`
- `control_state`
- `error_message`
- `payload`
- `result`
- `created_at`
- `started_at`
- `finished_at`
- `updated_at`

状态枚举：

```text
pending
running
paused
stopping
stopped
succeeded
failed
cancelled
```

任务类型：

```text
benchmark
judge
regex_judge
translate
import_dataset
sync_models
```

### 3.10 provider_call_logs

保存 provider 调用审计记录。

字段：

- `id`
- `provider`
- `model_name`
- `endpoint`
- `request_payload`
- `response_payload`
- `status_code`
- `latency_ms`
- `error_message`
- `created_at`

## 4. JSONB 字段策略

使用 JSONB 保存：

- choices。
- metadata。
- usage。
- payload。
- result。
- provider response。

JSONB 不用于替代核心关系字段。dataset、sample、model、task、run、judge 必须有结构化表。

## 5. 索引

建议索引：

```sql
CREATE INDEX idx_samples_dataset_language ON benchmark_samples(dataset_id, language);
CREATE INDEX idx_runs_sample_model ON benchmark_runs(sample_id, model_id);
CREATE INDEX idx_runs_status ON benchmark_runs(status);
CREATE INDEX idx_judge_run ON judge_results(benchmark_run_id);
CREATE INDEX idx_regex_judge_run ON regex_judge_results(benchmark_run_id);
CREATE INDEX idx_tasks_status_type ON task_queue(status, task_type);
CREATE INDEX idx_tasks_created_at ON task_queue(created_at);
CREATE INDEX idx_provider_logs_provider_model ON provider_call_logs(provider, model_name);
```

## 6. `.env` 数据库配置

```env
# ==================== PostgreSQL ====================
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=llm_benchmark_studio
POSTGRES_USER=llm_benchmark
POSTGRES_PASSWORD=change_me
POSTGRES_SSL_MODE=disable
DATABASE_URL=postgresql://llm_benchmark:change_me@localhost:5432/llm_benchmark_studio
```

## 7. Project Tree

PostgreSQL 本身没有代码目录，但项目中需要保留数据库相关文件：

```text
backend/
  apps/
    benchmarks/
      models.py
    llms/
      models.py
    evaluations/
      models.py
    taskqueue/
      models.py
  db/
    init/
      001_create_database.sql
    migrations_notes/
      schema_v1.md
docs/
  database/
    erd.md
    schema.md
```

## 8. 验收标准

- Django migration 可以创建完整 schema。
- 每个核心表包含 `activate` 或明确说明不需要。
- sample、translation、run 都有 language 或语言关联。
- LLM response、judge、regex judge 可以同时保存多个模型结果。
- task queue 状态可以被 SSE 查询并推送。
- 不需要修改原始 dataset JSON 也能返回包含 response / judge / regex judge 的组合结果。
