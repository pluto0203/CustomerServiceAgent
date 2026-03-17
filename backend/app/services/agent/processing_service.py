from __future__ import annotations

from collections import Counter
from time import perf_counter
from typing import Any
from uuid import UUID

from app.db.session import async_session
from app.models.customer import Customer
from app.repositories import (
    CustomerRepository,
    MessageLogRepository,
    RunResultRepository,
    WorkflowRunRepository,
)
from app.schemas.a2a_envelope import A2AMessage, A2APayloadType
from app.schemas.customer import CustomerBatch, CustomerRecord, DataSource
from app.skills.segment_insights import SegmentInsightsService


class AgentProcessingService:
    def __init__(self) -> None:
        self.segment_service = SegmentInsightsService()

    async def process_message(self, message: A2AMessage) -> dict[str, Any]:
        batch = await self._message_to_batch(message)

        async with async_session() as db:
            message_logs = MessageLogRepository(db)
            customers = CustomerRepository(db)
            workflow_runs = WorkflowRunRepository(db)
            run_results = RunResultRepository(db)

            await message_logs.create_received(message)
            await message_logs.mark_processing(message.message_id)

            run = await workflow_runs.create_pending(message, batch)
            await workflow_runs.mark_running(run)

            persisted_customers = await customers.upsert_batch(batch)
            skill_results = self._build_skill_results(persisted_customers)
            await run_results.create_many(run.id, skill_results)

            segment_distribution = self._segment_distribution(skill_results)
            result_summary = {
                "batch_id": str(batch.batch_id),
                "workflow_run_id": str(run.id),
                "record_count": len(persisted_customers),
                "records_succeeded": len(persisted_customers),
                "records_failed": 0,
                "skills": ["churn_prediction", "sentiment_analysis", "segment_insights"],
                "segment_distribution": segment_distribution,
                "status": "completed",
            }

            await workflow_runs.mark_completed(run, result_summary)
            await message_logs.mark_completed(message.message_id, run.id)
            await db.commit()

        segment_results = [item for item in skill_results if item["skill_name"] == "segment_insights"]
        segment_by_customer = {str(item["customer_id"]): item for item in segment_results}

        return {
            **result_summary,
            "results": [
                {
                    "customer_id": str(customer.id),
                    "churn_risk": None,
                    "sentiment": None,
                    "segment": segment_by_customer[str(customer.id)]["result_detail"],
                    "segment_label": segment_by_customer[str(customer.id)]["label"],
                    "status": "segment_ready",
                }
                for customer in persisted_customers
            ],
            "note": "Segment insights da chay that. Churn va sentiment van dang o muc placeholder.",
        }

    async def get_message_status(self, message_id: UUID) -> dict[str, Any]:
        async with async_session() as db:
            message_logs = MessageLogRepository(db)
            log = await message_logs.get_by_message_id(message_id)
            if log is None:
                return {
                    "message_id": str(message_id),
                    "status": "not_found",
                }

            return {
                "message_id": str(log.message_id),
                "status": log.status,
                "workflow_run_id": str(log.workflow_run_id) if log.workflow_run_id else None,
                "celery_task_id": log.celery_task_id,
                "source_agent_id": log.source_agent_id,
                "payload_type": log.payload_type,
                "error_detail": log.error_detail,
            }

    async def _message_to_batch(self, message: A2AMessage) -> CustomerBatch:
        payload = message.payload

        if message.payload_type == A2APayloadType.CUSTOMER_BATCH:
            return CustomerBatch.model_validate(payload)

        if message.payload_type == A2APayloadType.CUSTOMER_RECORD:
            record = CustomerRecord.model_validate(payload)
            return CustomerBatch(
                records=[record],
                source_agent_id=message.routing.source_agent_id,
            )

        if message.payload_type == A2APayloadType.TRACKING_EVENT:
            record = CustomerRecord(
                source=DataSource.WEBHOOK,
                extra_attributes=payload if isinstance(payload, dict) else {},
            )
            return CustomerBatch(
                records=[record],
                source_agent_id=message.routing.source_agent_id,
            )

        raise ValueError(
            f"payload_type '{message.payload_type.value}' chưa được hỗ trợ trong processing service"
        )

    def _build_skill_results(self, customers: list[Customer]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        segment_results = self.segment_service.analyze_many(customers)
        results.extend(segment_results)

        for customer in customers:
            for skill_name in ("churn_prediction", "sentiment_analysis"):
                results.append(
                    {
                        "customer_id": customer.id,
                        "skill_name": skill_name,
                        "label": None,
                        "score": None,
                        "confidence": None,
                        "summary": "Stub result persisted for workflow scaffolding.",
                        "result_detail": {"status": "pending_skill_implementation"},
                        "explainability": {},
                    }
                )
        return results

    def _segment_distribution(self, skill_results: list[dict[str, Any]]) -> dict[str, int]:
        counter = Counter(
            item["label"]
            for item in skill_results
            if item["skill_name"] == "segment_insights" and item.get("label")
        )
        return dict(counter)


async def process_message_timed(message: A2AMessage) -> tuple[dict[str, Any], float]:
    started = perf_counter()
    service = AgentProcessingService()
    result = await service.process_message(message)
    elapsed_ms = (perf_counter() - started) * 1000
    return result, elapsed_ms
