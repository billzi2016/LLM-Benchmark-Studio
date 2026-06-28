# RabbitMQ PRD - LLM Benchmark Studio Message Broker

## 1. 目标

RabbitMQ 作为 Celery broker，负责承载 LLM Benchmark Studio 的长任务消息。系统当前策略是一次只执行一个任务，优先保证稳定性，避免 provider 限流、Ollama 单并发阻塞、API 卡死。

## 2. 职责边界

RabbitMQ 负责：

- 接收 Django 提交的 Celery task message。
- 将 task 分发给 Celery worker。
- 支持任务确认、重试、失败处理。

RabbitMQ 不负责：

- 不保存业务结果。
- 不保存 benchmark response。
- 不作为任务状态主存储。

任务状态主存储是 PostgreSQL 的 `task_queue` 表。

## 3. 队列设计

当前版本建议只启用一个主执行队列：

```text
llm_benchmark.serial
```

原因：

- 一次只执行一个任务。
- Ollama 本地模型通常不适合高并发。
- 外部 API 容易限流。
- benchmark / judge / translate 都可能是长任务。

未来可扩展队列：

```text
llm_benchmark.import
llm_benchmark.benchmark
llm_benchmark.judge
llm_benchmark.translate
llm_benchmark.maintenance
```

但 v1 只要求 serial 队列。

## 4. Exchange 和 Routing Key

建议：

```text
exchange: llm_benchmark
type: direct
queue: llm_benchmark.serial
routing_key: task.serial
```

任务类型写入 Celery payload 和 PostgreSQL，不依赖多个 routing key 区分。

## 5. 消息格式

Celery message payload 必须包含：

```json
{
  "task_record_id": "uuid",
  "task_type": "benchmark",
  "dataset_id": "uuid",
  "sample_id": "uuid",
  "model_id": "uuid",
  "target_language": null,
  "created_by": "local-user"
}
```

业务详情以 PostgreSQL `task_queue.payload` 为准，RabbitMQ message 只放必要定位信息。

## 6. 可靠性规则

- Celery worker 开启 late ack。
- worker prefetch 设置为 1。
- 并发数设置为 1。
- 任务失败必须更新 PostgreSQL `task_queue.status=failed`。
- 任务开始必须更新 `task_queue.status=running`。
- 任务结束必须更新 `succeeded`、`failed`、`stopped` 或 `cancelled`。

推荐配置：

```env
# ==================== RabbitMQ ====================
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//
RABBITMQ_EXCHANGE=llm_benchmark
RABBITMQ_QUEUE_SERIAL=llm_benchmark.serial
RABBITMQ_ROUTING_KEY_SERIAL=task.serial
```

## 7. Celery Broker 配置要求

```env
# ==================== Celery Broker ====================
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_TASK_DEFAULT_QUEUE=llm_benchmark.serial
CELERY_WORKER_CONCURRENCY=1
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_TASK_ACKS_LATE=true
CELERY_TASK_REJECT_ON_WORKER_LOST=true
```

## 8. 运行和监控

RabbitMQ 管理界面可选：

```env
RABBITMQ_MANAGEMENT_PORT=15672
RABBITMQ_MANAGEMENT_ENABLED=true
```

Django `/api/system/status` 应展示：

- broker 是否可连接。
- serial queue 是否存在。
- 当前 ready 消息数。
- 当前 unacked 消息数。

## 9. Project Tree

RabbitMQ 配置在项目中建议放置：

```text
infra/
  rabbitmq/
    README.md
    rabbitmq.conf
    definitions.json
backend/
  config/
    celery.py
  apps/
    taskqueue/
      tasks.py
      services/
        broker_health.py
        task_control.py
```

如果使用 Docker Compose：

```text
infra/
  docker-compose.yml
  rabbitmq/
    rabbitmq.conf
    definitions.json
```

## 10. 验收标准

- Django 可以连接 RabbitMQ。
- Celery worker 可以从 `llm_benchmark.serial` 消费任务。
- worker 并发为 1。
- prefetch 为 1。
- RabbitMQ 中不保存业务结果。
- PostgreSQL 始终是任务状态来源。
