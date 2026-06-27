# Celery PRD - LLM Benchmark Studio Task Runtime

## 1. 目标

Celery 执行 LLM Benchmark Studio 的长任务，包括 dataset import、benchmark、judge、regex judge、translate、sync models。当前版本必须稳定优先：一次只运行一个任务，不做 batch，不做高并发。

Broker 使用 RabbitMQ，任务状态和结果写入 PostgreSQL，进度通过 Django SSE 推送给 Vue。

## 2. 核心原则

- `worker_concurrency=1`。
- `worker_prefetch_multiplier=1`。
- 每次任务处理一个 sample 或一个明确的单元。
- 不在 Django API 请求线程中执行 LLM 调用。
- 每个任务必须有 PostgreSQL task record。
- 每个任务必须持续更新进度。
- pause / stop 控制状态保存到 PostgreSQL，由任务执行循环主动检查。
- Celery task 函数只做 orchestration，不写成巨型业务函数。
- benchmark、judge、regex judge、translate 逻辑分别放入独立 runner service。
- 任务状态更新、provider 调用、prompt 构造、错误处理必须复用共享 service。
- 新增任务类型必须通过 task registry 或清晰的 service 边界扩展。
- 不重复实现 provider timeout、重试、日志和 response normalization。

原则上不自己造轮子。优先使用成熟套件：

- Celery 官方 task、routing、retry、signal 能力。
- django-celery-results 保存 Celery 结果元信息。
- RabbitMQ 原生 ack、prefetch、durable queue。
- Django ORM 管理 task record。
- pytest + Celery eager mode 做单元测试。

## 3. 任务类型

### 3.1 import_dataset

职责：

- 从 `data/benchmark_datasets/` 读取 JSON。
- 校验 dataset schema。
- 写入 `datasets` 和 `benchmark_samples`。
- 设置 `language` 和 `activate`。

### 3.2 benchmark

职责：

- 读取一个 sample。
- 构造 prompt。
- 调用目标 provider / model。
- 抽取最终答案。
- 不保存 think。
- 写入 `benchmark_runs`。
- 更新 task progress。

Prompt 要求：

```text
You are answering a benchmark multiple-choice question.
Return only the option letter, such as A, B, C, or D.
Do not explain.
Do not include reasoning.

Question:
...

Choices:
A. ...
B. ...
C. ...
D. ...

Answer:
```

如果模型支持 think，可以让 provider 使用 think，但保存时必须丢弃 think，只保存最终答案。

### 3.3 judge

职责：

- 读取 benchmark run。
- 将原始题目、选项、标准答案、模型最终答案打包到 judge prompt。
- 调用 judge provider / judge model。
- 判断是否 match。
- 写入 `judge_results`。

默认：

```env
JUDGE_PROVIDER=ollama
JUDGE_MODEL=gpt-oss:20b
```

### 3.4 regex_judge

职责：

- 对已有 benchmark run 正则判断。
- 可以使用同一个 judge model，也可以使用 `.env` 中新的 judge 配置。
- 写入 `regex_judge_results`。
- 不覆盖 `judge_results`。

### 3.5 translate

职责：

- 读取 sample。
- 判断 source language 是否等于 target language。
- 如果相同，任务直接标记 succeeded，并说明 skipped。
- 如果不同，调用 translate provider / model。
- 写入 `translations`。

默认：

```env
TRANSLATE_PROVIDER=ollama
TRANSLATE_MODEL=gpt-oss:20b
```

### 3.6 sync_models

职责：

- 从 `data/llm_model_names.json` 读取模型。
- 可选读取 Ollama list 结果后由用户确认写入 JSON。
- 同步到 PostgreSQL `llm_models`。

## 4. 任务控制

### 4.1 Play

前端点击 Play：

```text
POST /api/tasks/{task_id}/play
```

Django 将 pending / paused 任务投递或恢复为可执行状态。

### 4.2 Pause

前端点击 Pause：

```text
POST /api/tasks/{task_id}/pause
```

规则：

- API 将 `control_state=pause_requested`。
- Celery task 在安全点检查 control state。
- 当前 LLM 单次调用不能强制中断，只能在调用返回后暂停。

### 4.3 Stop

前端点击 Stop：

```text
POST /api/tasks/{task_id}/stop
```

规则：

- API 将 `control_state=stop_requested`。
- Celery task 在安全点停止。
- 当前 provider 调用如果无法中断，等待调用返回后标记 stopped。

## 5. 进度更新

Celery 每个阶段更新：

- `progress_current`
- `progress_total`
- `progress_percent`
- `status`
- `error_message`
- `updated_at`

Django SSE 读取 PostgreSQL 或订阅内部事件后推送：

```json
{
  "task_id": "uuid",
  "status": "running",
  "progress_percent": 42,
  "message": "Calling judge model"
}
```

## 6. 错误处理

错误分类：

- provider timeout。
- provider rate limit。
- provider invalid response。
- dataset schema invalid。
- database write failed。
- task stopped。
- task paused。

失败任务必须写入：

- `status=failed`
- `error_message`
- provider call log

## 7. `.env` 配置

```env
# ==================== Celery ====================
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=django-db
CELERY_TASK_DEFAULT_QUEUE=llm_benchmark.serial
CELERY_WORKER_CONCURRENCY=1
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_TASK_ACKS_LATE=true
CELERY_TASK_REJECT_ON_WORKER_LOST=true
CELERY_TASK_TIME_LIMIT=3600
CELERY_TASK_SOFT_TIME_LIMIT=3300

# ==================== Task Runtime ====================
TASK_SINGLE_ACTIVE_ONLY=true
TASK_DEFAULT_TIMEOUT_SECONDS=3600
TASK_PROVIDER_TIMEOUT_SECONDS=600
TASK_MAX_RETRIES=0
TASK_PROGRESS_POLL_INTERVAL_SECONDS=1
TASK_SAVE_PROVIDER_LOGS=true
```

## 8. Project Tree

```text
backend/
  config/
    celery.py
  apps/
    taskqueue/
      __init__.py
      models.py
      tasks.py
      services/
        task_runner.py
        task_control.py
        progress.py
        locks.py
        broker_health.py
    evaluations/
      services/
        benchmark_runner.py
        judge_runner.py
        regex_judge_runner.py
        translate_runner.py
    benchmarks/
      services/
        dataset_importer.py
        prompt_builder.py
        answer_normalizer.py
    llms/
      providers/
        base.py
        ollama.py
        openai.py
        openrouter.py
        vllm.py
        sglang.py
      services/
        generation.py
        registry.py
```

## 9. 验收标准

- Celery worker 一次只执行一个任务。
- pending 任务不会自动并发运行。
- benchmark / judge / regex judge / translate 均可作为单任务执行。
- pause / stop 能改变 task control state。
- 任务进度写入 PostgreSQL。
- Vue 可以通过 SSE 看到进度变化。
- Provider 调用失败不会导致 worker 崩溃。
