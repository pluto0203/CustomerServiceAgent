# Phase 1 Execution Plan - Customer Behavior AI Agent

## 1) Muc tieu Phase 1

Xay dung MVP backend-first co the van hanh end-to-end tren du lieu thuc, tao gia tri ngay cho Marketing va CSKH voi 3 nang luc:

1. Du doan churn risk theo khach hang.
2. Phan tich sentiment tu review/ticket.
3. Tong hop insight theo segment de de ra hanh dong.

## 1b) Dinh vi kien truc: Multi-Agent System

Agent phan tich hanh vi khach hang nay la MOT MODULE trong he thong MultiAgentAssistant lon hon.
Dieu nay co nghia:

- **Dau vao chinh** khong phai CSV hay CRM truc tiep, ma la JSON output tu mot Agent khac trong he thong
  (vi du: DataCollector Agent, CRM Sync Agent, ETL Agent).
- **Canonical Customer Schema** dong thoi la **A2A (Agent-to-Agent) contract** — hop dong giao tiep
  giua cac agent.
- **CRM connector / CSV ingestion** van con nhung la fallback hoac la viec cua agent upstream, khong
  phai cua module nay.
- Module nay expose mot **Agent Input Endpoint** nhan JSON theo envelope chuan, xu ly, roi dua
  vao pipeline phan tich.

```
MultiAgentAssistant Orchestrator
         |
         |── DataCollector Agent  ──┐
         |── CRM Sync Agent  ───────┤──► JSON (A2A Envelope)
         |── ETL Pipeline Agent  ───┘
                                     |
                                     ▼
              [Customer Behavior Analysis Agent - module nay]
                    |
                    |── Ingest & Normalize (theo Canonical Schema)
                    |── Vector Embed & Index
                    |── Skill: Churn / Sentiment / Segment
                    |
                    ▼
              JSON Result Output  ──►  Orchestrator hoac UI
```

## 2) Scope bat buoc (in-scope)

### Core platform

- FastAPI backend voi auth co ban, API versioning, run management.
- Agent orchestration theo graph (LangGraph) + skill registry.
- Semantic memory retrieval tu vector DB (Qdrant).
- Async execution qua Celery + Redis.
- Logging, metrics, tracing co ban.

### Skills MVP

- Churn Risk Predictor (batch scoring + top drivers).
- Sentiment Analyzer (positive/neutral/negative + trend).
- Segment Insight Summary (cluster/segment + recommendation text).

### Data ingestion MVP (uu tien)

- **Agent Input Receiver**: nhan JSON A2A envelope tu agent upstream (priority #1).
- Data quality validation va normalization ve Canonical Customer Schema.
- Webhook endpoint cho tracking event tu agent khac.
- CSV uploader (fallback / testing, priority #2).
- CRM connector truc tiep (optional cho Phase 1, agent khac co the xu ly thay).

### UI toi thieu (support backend launch)

- Workflow canvas co ban: data source -> skill -> output.
- Run trigger + status + result table/chart.

## 3) Out-of-scope trong Phase 1

- Multi-tenant full isolation.
- Real-time stream processing quy mo lon.
- Skill marketplace cong khai.
- Tu dong toi uu campaign closed-loop.

## 4) Architecture focus cho Phase 1

## Data flow

1. Ingestion service nhan CSV/CRM/webhook.
2. Standardization layer map ve schema Customer 360 toi thieu.
3. Batch pipeline tao features + embedding cho text.
4. Structured data vao Postgres/DuckDB; embedding vao Qdrant.
5. Orchestrator doc workflow graph va invoke skill theo node.
6. Skill query data + semantic context, tra output co schema.
7. Result store ghi run artifact, score table, summary.
8. API tra ket qua cho UI va export.

## 5) Work breakdown theo 4 stream

### Stream A - Platform Backend

- API gateway va endpoint domain (workflow, run, ingestion, skills).
- Auth JWT co ban, role owner/editor/viewer.
- Config management, dependency injection, error contracts.
- ORM models + repository layer + migration baseline.

### Stream B - Agent va AI Integration

- LangGraph runtime: node contracts, retry, timeout.
- LLM provider abstraction (OpenAI + fallback provider).
- Prompt templates + output schema validation.
- Evaluation harness cho skill output quality.

### Stream C - Data Pipeline va ML

- Canonical schema + mapping rules.
- Feature pipeline cho churn (RFM, support frequency, activity decay).
- Sentiment pipeline cho text + topic extraction.
- Model training baseline, model registry toi thieu.

### Stream D - UX toi thieu cho workflow

- Visual node editor toi gian.
- Run monitoring va output page.
- Error surface ro rang cho ingestion va skill run.

## 6) Ke hoach 10 tuan (chi tiet)

## Tuan 1-2: Foundation va contracts

- Chot schema du lieu toi thieu va contracts API.
- Dung khung service, migration dau tien, health endpoints.
- Dung skeleton LangGraph + skill interface.
- Dung CI co test va docker build gate.

Definition of done:

- Co API health, auth mock, workflow CRUD mock.
- Co migration baseline + seed du lieu test.
- CI pass tren pull request.

## Tuan 3-4: Ingestion va storage

- CSV ingestion + validation + dead-letter record.
- CRM connector ban dau.
- Webhook tracking event endpoint.
- Pipeline embedding va index vao Qdrant.

Definition of done:

- Du lieu vao Postgres va Qdrant dung schema.
- Co report data quality (missing/invalid/duplicate).

## Tuan 5-6: Skill 1 + Skill 2

- Churn model baseline (scikit-learn/XGBoost).
- Sentiment baseline (transformers pipeline) + trend.
- Skill output schema co confidence + explainers.
- Luu run artifact va model/prompt version.

Definition of done:

- Churn va sentiment chay duoc tren du lieu that.
- Ket qua truy xuat duoc theo run id.

## Tuan 7-8: Skill 3 + orchestration hardening

- Segment & Insight Summary skill.
- Retry policy, timeout, cancellation, idempotency key.
- Prompt guardrail va fallback model.
- Monitoring dashboard co ban.

Definition of done:

- Workflow 3-skill chay end-to-end on-demand.
- Co trace mot run tu API den tung node.

## Tuan 9: UAT voi du lieu pilot

- Chay pilot voi 1-2 bo du lieu doanh nghiep.
- Tune threshold churn va sentiment mapping.
- Fix bug theo feedback nguoi dung nghiep vu.

Definition of done:

- Team nghiep vu xac nhan insight huu ich va de hieu.

## Tuan 10: Stabilization va release MVP

- Freeze feature, chi fix bug P0/P1.
- Hoan thien runbook van hanh + backup/restore.
- Release candidate + checklist Go/No-Go.

Definition of done:

- He thong dat tieu chi release ben duoi.

## 7) KPI va quality gates

## Product KPI

- Time-to-insight < 15 phut cho 100k records batch.
- >= 70% pilot users danh gia insight la actionable.
- Ty le run thanh cong >= 95%.

## ML KPI

- Churn model AUC >= 0.75 (baseline).
- Recall@top20% risk >= 0.60.
- Sentiment macro-F1 >= 0.70 tren tap validation.

## Engineering KPI

- P95 API latency (non-ML endpoints) < 500ms.
- CI success rate >= 90%/tuan.
- Mean time to recovery (MTTR) < 2h cho P1.

## 8) Backlog uu tien (P0/P1/P2)

### P0 (phai co)

- Ingestion CSV + 1 CRM connector.
- Churn skill, sentiment skill.
- Workflow run + result persistence.
- Logging/tracing + CI + Docker deployment.

### P1 (nen co)

- Segment insight skill.
- Role-based access co ban.
- Export report CSV.

### P2 (de sau)

- Multi-tenant isolation.
- Real-time scoring near real-time.
- Auto-suggestion workflow templates.

## 9) Risk register va giam thieu

1. Du lieu thieu va khong dong nhat
- Giam thieu: mapping UI + data contract + quality score.

2. Model drift hoac ket qua khong on dinh
- Giam thieu: model/prompt versioning + periodic re-eval.

3. Latency cao do chain LLM
- Giam thieu: cache retrieval, summary truncation, async run.

4. Team nghiep vu kho tin vao output
- Giam thieu: explainability (top factors), confidence score, examples.

## 10) Release checklist Go/No-Go

- Da dat tat ca KPI toi thieu cua pilot.
- Khong con bug P0, bug P1 da co workaround ro rang.
- Co dashboard monitoring + alert co ban.
- Co runbook rollback va backup DB.
- Team CSKH/Marketing test va sign-off UAT.

## 11) Tai nguyen de xuat

- 1 Backend engineer.
- 1 ML/AI engineer.
- 1 Frontend engineer (part-time o Tuan 1-4, full-time tu Tuan 5).
- 1 Product owner (part-time).

## 12) Next action ngay trong tuan nay

1. Chot CRM connector dau tien.
2. Chot canonical customer schema v1.
3. Chot bo metric danh gia churn/sentiment.
4. Khoi tao 3 dataset mau cho integration test.
5. Tao issue backlog theo P0/P1/P2 va gan owner.
