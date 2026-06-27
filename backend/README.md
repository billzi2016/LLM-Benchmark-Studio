# Backend

Django API backend for LLM Benchmark Studio.

Run locally:

```bash
cd backend
python manage.py runserver 6325
```

Run tests:

```bash
cd backend
python manage.py test tests
```

Initial API endpoints:

- `GET /api/system/status`
- `GET /api/models`
- `GET /api/languages`
- `GET /api/datasets`
- `GET /api/datasets/{dataset_name}`
- `GET /api/llms/ollama/health`
- `POST /api/llms/ollama/generate`
- `GET /api/llms/providers`
- `GET /api/llms/{provider_name}/health`
- `POST /api/llms/{provider_name}/generate`
