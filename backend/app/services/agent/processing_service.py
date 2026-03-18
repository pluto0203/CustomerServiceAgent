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
from app.skills import ChurnPredictionService, SegmentInsightsService, SentimentAnalysisService


class AgentProcessingService:
    def __init__(self) -> None:
        self.churn_service = ChurnPredictionService()
        self.segment_service = SegmentInsightsService()
        self.sentiment_service = SentimentAnalysisService()

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
        churn_results = [item for item in skill_results if item["skill_name"] == "churn_prediction"]
        sentiment_results = [item for item in skill_results if item["skill_name"] == "sentiment_analysis"]
        segment_by_customer = {str(item["customer_id"]): item for item in segment_results}
        churn_by_customer = {str(item["customer_id"]): item for item in churn_results}
        sentiment_by_customer = {str(item["customer_id"]): item for item in sentiment_results}

        return {
            **result_summary,
            "results": [
                self._build_customer_result(
                    customer,
                    segment_by_customer[str(customer.id)],
                    churn_by_customer[str(customer.id)],
                    sentiment_by_customer[str(customer.id)],
                )
                for customer in persisted_customers
            ],
            "note": "Ca 3 skill churn, sentiment, segment da duoc thuc thi bang ruleset runtime.",
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
        results.extend(self.churn_service.analyze_many(customers))
        results.extend(self.sentiment_service.analyze_many(customers))
        results.extend(self.segment_service.analyze_many(customers))
        return results

    def _segment_distribution(self, skill_results: list[dict[str, Any]]) -> dict[str, int]:
        counter = Counter(
            item["label"]
            for item in skill_results
            if item["skill_name"] == "segment_insights" and item.get("label")
        )
        return dict(counter)

    def _build_customer_result(
        self,
        customer: Customer,
        segment_result: dict[str, Any],
        churn_result: dict[str, Any],
        sentiment_result: dict[str, Any],
    ) -> dict[str, Any]:
        detail = dict(segment_result.get("result_detail") or {})
        explainability = dict(segment_result.get("explainability") or {})
        top_signals = list(explainability.get("top_signals") or [])
        churn_detail = dict(churn_result.get("result_detail") or {})
        sentiment_detail = dict(sentiment_result.get("result_detail") or {})
        churn_explainability = dict(churn_result.get("explainability") or {})
        sentiment_explainability = dict(sentiment_result.get("explainability") or {})
        recommendations = self._merge_unique(
            list(detail.get("recommended_actions") or []),
            list(churn_detail.get("recommended_actions") or []),
            list(sentiment_detail.get("recommended_actions") or []),
        )
        merged_signals = self._merge_unique(
            top_signals,
            list(churn_explainability.get("top_factors") or []),
            list(sentiment_explainability.get("top_signals") or []),
        )

        return {
            "customer_id": str(customer.id),
            "email": customer.email,
            "churn_risk": churn_result.get("score"),
            "sentiment": sentiment_result.get("label"),
            "core_insight": self._build_core_insight(segment_result, churn_result, sentiment_result),
            "recommendations": recommendations,
            "top_signals": merged_signals,
            "churn": {
                **churn_detail,
                "summary": churn_result.get("summary"),
                "top_factors": list(churn_explainability.get("top_factors") or []),
                "score": churn_result.get("score"),
                "confidence": churn_result.get("confidence"),
            },
            "sentiment_detail": {
                **sentiment_detail,
                "summary": sentiment_result.get("summary"),
                "top_signals": list(sentiment_explainability.get("top_signals") or []),
                "score": sentiment_result.get("score"),
                "confidence": sentiment_result.get("confidence"),
            },
            "segment": {
                **detail,
                "summary": segment_result.get("summary"),
                "top_signals": top_signals,
            },
            "segment_label": segment_result.get("label"),
            "status": "analysis_ready",
        }

    def _build_core_insight(
        self,
        segment_result: dict[str, Any],
        churn_result: dict[str, Any],
        sentiment_result: dict[str, Any],
    ) -> str:
        segment_summary = segment_result.get("summary") or ""
        churn_label = churn_result.get("label") or "unknown"
        sentiment_label = sentiment_result.get("label") or "neutral"
        return f"{segment_summary} Churn risk {churn_label}; sentiment {sentiment_label}.".strip()

    def _merge_unique(self, *groups: list[str]) -> list[str]:
        merged: list[str] = []
        for group in groups:
            for item in group:
                if item and item not in merged:
                    merged.append(item)
        return merged


async def process_message_timed(message: A2AMessage) -> tuple[dict[str, Any], float]:
    started = perf_counter()
    service = AgentProcessingService()
    result = await service.process_message(message)
    elapsed_ms = (perf_counter() - started) * 1000
    return result, elapsed_ms
