# API Design PRD - LLM Benchmark Studio

## 1. 目标

本文定义 LLM Benchmark Studio 的 API 设计规范。后端使用 Django Ninja，前端 Vue 通过 typed API client 调用。API 必须稳定、可读、可验证，并为后续鉴权、多用户和部署扩展预留空间。

## 2. 设计原则

- REST API 负责资源读写和任务控制。
- SSE 负责任务状态和进度推送。
- 长任务只通过 Celery 执行。
- API response 格式统一。
- request / response 全部使用 Ninja schema。
- API 不返回 provider secret。
- API 不返回不可信 HTML。
- 路由、schema、service 分层，避免重复逻辑。

## 3. URL 规范

统一前缀：

```text
/api
```

资源使用复数名词：

```text
/api/models
/api/datasets
/api/languages
/api/tasks
/api/results
```

动作型接口只用于明确控制命令：

```text
POST /api/tasks/{task_id}/play
POST /api/tasks/{task_id}/pause
POST /api/tasks/{task_id}/stop
POST /api/tasks/{task_id}/retry
```

## 4. Response 格式

成功响应：

```json
{
  "ok": true,
  "data": {},
  "meta": {}
}
```

列表响应：

```json
{
  "ok": true,
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 50,
    "total": 120
  }
}
```

错误响应：

```json
{
  "ok": false,
  "error": {
    "code": "TASK_ALREADY_RUNNING",
    "message": "Another task is already running.",
    "details": {}
  }
}
```

## 5. HTTP 状态码

- `200`：读取或控制成功。
- `201`：创建成功。
- `202`：任务已接受，等待执行。
- `400`：请求参数错误。
- `401`：未认证，预留。
- `403`：CSRF、权限或 origin 不允许。
- `404`：资源不存在。
- `409`：状态冲突，例如已有 running task。
- `422`：schema 通过但业务语义不合法。
- `500`：服务端错误。
- `503`：依赖服务不可用，例如 PostgreSQL/RabbitMQ/Celery。

## 6. 核心接口

```text
GET  /api/system/status
GET  /api/models
GET  /api/datasets
GET  /api/languages
GET  /api/tasks
GET  /api/tasks/{task_id}
POST /api/tasks/benchmark
POST /api/tasks/judge
POST /api/tasks/regex judge
POST /api/tasks/translate
POST /api/tasks/{task_id}/play
POST /api/tasks/{task_id}/pause
POST /api/tasks/{task_id}/stop
GET  /api/results
GET  /api/results/{result_id}
GET  /api/results/export
GET  /api/events/tasks
```

## 7. Task 创建请求

Benchmark：

```json
{
  "dataset_id": "uuid",
  "sample_id": "uuid",
  "model_id": "uuid"
}
```

Judge：

```json
{
  "benchmark_run_id": "uuid"
}
```

Regex judge：

```json
{
  "benchmark_run_id": "uuid",
  "judge_model_id": "uuid"
}
```

Translate：

```json
{
  "sample_id": "uuid",
  "target_language": "fr"
}
```

## 8. Task 状态模型

```json
{
  "id": "uuid",
  "task_type": "benchmark",
  "status": "running",
  "control_state": "none",
  "progress_current": 1,
  "progress_total": 1,
  "progress_percent": 50,
  "dataset": {},
  "sample": {},
  "model": {},
  "target_language": null,
  "error_message": null,
  "created_at": "...",
  "updated_at": "..."
}
```

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

## 9. SSE 设计

连接：

```text
GET /api/events/tasks
```

事件类型：

```text
task.created
task.updated
task.finished
task.failed
system.status
```

事件示例：

```text
event: task.updated
data: {"task_id":"uuid","status":"running","progress_percent":42,"message":"Calling provider"}
```

前端规则：

- 断线自动重连。
- 重连后调用 `GET /api/tasks` 拉取快照。
- SSE 数据只作为增量更新，不作为唯一真实来源。

## 9.1 Results Export

导出全部结果：

```text
GET /api/results/export
```

可选过滤参数：

```text
dataset_id
model_id
language
status
created_after
created_before
```

响应：

```text
Content-Type: application/zip
Content-Disposition: attachment; filename="llm-benchmark-results-YYYYMMDD-HHMMSS.zip"
```

ZIP 内容建议：

```text
manifest.json
results/
  benchmark_results.json
  translations.json
  tasks.json
```

要求：

- ZIP 必须压缩。
- JSON 使用 UTF-8。
- 不导出 provider API key。
- 大数据导出使用 streaming response 或临时文件。

## 10. CSRF / CORS / XSS

CSRF：

- 如果使用 cookie/session 认证，所有 mutating API 必须校验 CSRF。
- 前端 API client 必须发送 `X-CSRFToken`。
- 不允许为了开发方便全局关闭 CSRF。

CORS：

- 使用 `django-cors-headers`。
- 只允许 `.env` 中的 `FRONTEND_ALLOWED_ORIGINS`。
- 生产环境禁止 `CORS_ALLOW_ALL_ORIGINS=true`。

XSS：

- API 返回 dataset、LLM response、judge reason 时全部视为不可信文本。
- 不返回 HTML snippet。
- 前端不使用不可信 `v-html`。
- 生产环境启用 CSP。

## 11. 分页和过滤

列表接口默认分页：

```text
page=1
page_size=50
```

最大 `page_size=200`。

常用过滤：

```text
GET /api/tasks?status=running&task_type=benchmark
GET /api/results?dataset_id=...&model_id=...
GET /api/datasets?activate=true
```

## 12. 版本策略

初始版本使用：

```text
/api
```

未来破坏性变更使用：

```text
/api/v2
```

OpenAPI schema 由 Django Ninja 生成，前端类型可从 schema 自动生成，避免手写重复类型。

## 13. 验收标准

- API schema 可自动生成。
- 前端 API client 不重复拼接 endpoint。
- 所有 mutating API 有 CSRF 策略。
- 所有 response 使用统一格式。
- 所有错误使用统一 error code。
- SSE 事件格式稳定。
- API 不暴露 provider secret。
