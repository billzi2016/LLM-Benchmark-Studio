# Quickstart

This is the shortest path to run the full local stack with the real PostgreSQL + RabbitMQ + Django + Celery + Vue workflow, plus the host-side FastAPI system profiler.

Default Django admin:

```text
http://localhost:6341/admin
username: guest
password: guest
```

## 1. Prepare

From the project root:

```bash
cp .env.example .env
```

Edit `.env` if you need to change database password, provider settings, or ports.

## 2. Start Everything

Run the full stack:

```bash
docker compose up --build -d worker backend rabbitmq postgres frontend
```

This starts:

- `postgres`
- `rabbitmq`
- `backend`
- `worker`
- `frontend`

## 3. Start the Host System Profiler

Run the system profiler on the host machine, outside Docker:

```bash
PYTHONPATH=backend python3 -m uvicorn system_profiler.api:app --host 127.0.0.1 --port 6346
```

This service exposes:

- `http://127.0.0.1:6346/health`
- `http://127.0.0.1:6346/snapshot`
- `http://127.0.0.1:6346/history`
- `http://127.0.0.1:6346/stream`

The Vue frontend reads system metrics directly from this FastAPI service.

## 4. Open the UI

After startup:

- Frontend: `http://localhost:6342`
- Backend API: `http://localhost:6341/api/system/status`
- Swagger: `http://localhost:6341/api/docs`
- OpenAPI JSON: `http://localhost:6341/api/openapi.json`
- RabbitMQ UI: `http://localhost:15672`
- System profiler health: `http://127.0.0.1:6346/health`

Default RabbitMQ credentials:

```text
guest / guest
```

## 5. Check Logs

Project logs are written to:

```text
logs/
```

Live logs:

```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend
docker compose logs -f postgres
docker compose logs -f rabbitmq
```

`llm_walltime` is also written into `logs/` as a timestamped file.

Default saved log files include:

```text
YYYYMMDD-HHMMSS-backend.log
YYYYMMDD-HHMMSS-worker.log
YYYYMMDD-HHMMSS-frontend.log
YYYYMMDD-HHMMSS-postgres.log
YYYYMMDD-HHMMSS-rabbitmq.log
YYYYMMDD-HHMMSS-rabbitmq-sasl.log
YYYYMMDD-HHMMSS-llm_walltime.log
```

## 6. Run Database Migrations Manually

Backend startup already runs migrations automatically.

If you want to run them yourself:

```bash
docker compose exec backend python manage.py migrate
```

## 7. Restart One Service

Examples:

```bash
docker compose restart backend
docker compose restart worker
docker compose restart frontend
```

## 8. Stop Everything

Stop services and keep data:

```bash
docker compose down
```

Stop services and remove volumes:

```bash
docker compose down -v
```

## 9. Verify the Worker Is Alive

Check service state:

```bash
docker compose ps
```

Check worker logs:

```bash
docker compose logs -f worker
```

Check backend health:

```bash
curl http://localhost:6341/api/system/status
```

The `Service Health` section should show:

- Django API
- PostgreSQL
- RabbitMQ
- Celery Worker
