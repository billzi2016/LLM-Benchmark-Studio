# 快速启动

这是当前项目最短的可运行路径，直接启动真实的 PostgreSQL + RabbitMQ + Django + Celery + Vue 全链路，再加上宿主机侧的 FastAPI system profiler。

默认 Django admin：

```text
http://localhost:6341/admin
用户名: guest
密码: guest
```

## 1. 准备环境变量

在项目根目录执行：

```bash
cp .env.example .env
```

如果你需要修改数据库密码、provider 配置或者端口，再手动编辑 `.env`。

## 2. 启动完整服务

执行：

```bash
docker compose up --build -d worker backend rabbitmq postgres frontend
```

这条命令会启动：

- `postgres`
- `rabbitmq`
- `backend`
- `worker`
- `frontend`

## 3. 启动宿主机 System Profiler

这个服务不要放进 Docker。直接在宿主机启动：

```bash
PYTHONPATH=backend python3 -m uvicorn system_profiler.api:app --host 127.0.0.1 --port 6346
```

它会提供这些接口：

- `http://127.0.0.1:6346/health`
- `http://127.0.0.1:6346/snapshot`
- `http://127.0.0.1:6346/history`
- `http://127.0.0.1:6346/stream`

Vue 前端会直接读取这个 FastAPI 服务的系统监控数据和 profiler 状态，Django 不会代理或二次检查它。

## 4. 打开页面

启动完成后访问：

- 前端：`http://localhost:6325`
- 后端 API：`http://localhost:6341/api/system/status`
- Swagger：`http://localhost:6341/api/docs`
- OpenAPI JSON：`http://localhost:6341/api/openapi.json`
- RabbitMQ 管理页面：`http://localhost:15672`
- System profiler health：`http://127.0.0.1:6346/health`

RabbitMQ 默认账号密码：

```text
guest / guest
```

## 5. 看日志

项目日志会写到：

```text
logs/
```

实时查看：

```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend
docker compose logs -f postgres
docker compose logs -f rabbitmq
```

模型运行耗时日志 `llm_walltime` 也会按时间戳写进 `logs/`。

默认会保存这些日志文件：

```text
YYYYMMDD-HHMMSS-backend.log
YYYYMMDD-HHMMSS-worker.log
YYYYMMDD-HHMMSS-frontend.log
YYYYMMDD-HHMMSS-postgres.log
YYYYMMDD-HHMMSS-rabbitmq.log
YYYYMMDD-HHMMSS-rabbitmq-sasl.log
YYYYMMDD-HHMMSS-llm_walltime.log
```

## 6. 手动执行数据库迁移

backend 启动时已经会自动执行迁移。

如果你要手动再跑一遍：

```bash
docker compose exec backend python manage.py migrate
```

## 7. 单独重启某个服务

例如：

```bash
docker compose restart backend
docker compose restart worker
docker compose restart frontend
```

## 8. 停止服务

停止服务但保留数据：

```bash
docker compose down
```

停止服务并删除卷：

```bash
docker compose down -v
```

## 9. 确认 Worker 真的活着

先看服务状态：

```bash
docker compose ps
```

再看 worker 日志：

```bash
docker compose logs -f worker
```

再看后端健康接口：

```bash
curl http://localhost:6341/api/system/status
```

前端左侧 `Service Health` 理论上应该看到：

- Django API
- PostgreSQL
- RabbitMQ
- Celery Worker
- System Profiler
