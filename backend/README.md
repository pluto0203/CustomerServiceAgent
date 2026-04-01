# Backend Structure (Phase 1 MVP)

## Folder Structure

```text
backend/
  app/
    api/
      v1/
        endpoints/          # FastAPI endpoints by domain
    connectors/
      crm/                  # CRM connectors (HubSpot/Zoho in later steps)
      tracking/             # Tracking/webhook ingestion connectors
    core/                   # Settings, security, dependency injection
    db/                     # DB session, base model, engine setup
    models/                 # SQLAlchemy ORM models
    repositories/           # Data access layer
    schemas/                # Pydantic request/response schemas
    services/
      agent/                # Agent orchestration service (LangGraph entrypoint)
      ingestion/            # Data ingestion + normalization services
      llm/                  # LLM provider abstraction, prompt handling
      memory/               # Semantic memory retrieval/storage wrappers
    skills/
      churn_prediction/     # Skill: churn scoring and explainability
      sentiment_analysis/   # Skill: customer feedback sentiment analysis
      segment_insights/     # Skill: customer segment and insight summary
    tasks/                  # Celery task definitions
    workflows/              # Workflow execution graph and node contracts
    observability/          # Tracing, metrics, structured logging
    utils/                  # Shared helpers/utilities
  alembic/
    versions/               # Database migration files
  configs/                  # Environment-specific config templates
  pipelines/                # Batch data pipeline scripts/jobs
  scripts/                  # Operational scripts (seed, maintenance)
  workers/                  # Celery worker startup and settings
  tests/                    # Unit/integration tests
  requirements.txt          # Python dependencies for Phase 1
  README.md
```

## Notes

- Keep business logic in `services/` and `skills/`, not in API handlers.
- `skills/` should implement a common contract for pluggable execution.
- `workflows/` owns graph/node orchestration logic, separate from skill internals.
- `repositories/` reduces coupling between services and ORM models.

## DevOps and Packaging Files

- Root `docker-compose.yml`: local stack for API, worker, PostgreSQL, Redis, and Qdrant.
- Root `.dockerignore`: reduces Docker build context and image size.
- Root `.gitignore`: keeps runtime artifacts and secrets out of Git.
- Root `Makefile`: common commands for local Docker lifecycle and tests.
- `backend/Dockerfile`: production-oriented Python image for API and worker.
- `backend/.env.example`: baseline environment variables for local/dev.
- `.github/workflows/ci-backend.yml`: GitHub Actions pipeline for tests and Docker build check.

## Quick Start

```bash
# from repository root
make up

# run tests locally
make test

# stop services
make down
```

## Local LLM for Skill Endpoints

MVP flow:

1. Upload customer data via CSV.
2. Call each skill endpoint (churn, sentiment, segment).
3. Skill runtime will try LLM first, and fallback to rule-based when LLM is unavailable or output is invalid.

### 1) Configure local model endpoint

Set these env vars in `backend/.env`:

```env
LLM_PROVIDER=local
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:7b-instruct
LLM_API_KEY=
```

Notes:

- `LLM_BASE_URL` must point to an OpenAI-compatible API.
- Example providers: Ollama, LM Studio, vLLM.
- For providers requiring a key, put it in `LLM_API_KEY`.

### 2) CSV ingestion endpoint

```http
POST /api/v1/agent/ingest/csv
Content-Type: multipart/form-data
file=<customers.csv>
```

### 3) Run each skill endpoint

```http
POST /api/v1/skills/churn-prediction/run
POST /api/v1/skills/sentiment-analysis/run
POST /api/v1/skills/segment-insights/run
```

Request body:

```json
{
  "customer_ids": null,
  "limit": 500
}
```

Optional:

- Set `customer_ids` to run specific customers only.
- Keep `customer_ids` null to run by `limit`.

### Runtime wiring

- Shared local/cloud LLM gateway: `app/services/llm/client.py`
- Skill adapters:
  - `app/skills/churn_prediction/main.py`
  - `app/skills/sentiment_analysis/main.py`
  - `app/skills/segment_insights/main.py`
