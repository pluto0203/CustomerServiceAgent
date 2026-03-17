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
