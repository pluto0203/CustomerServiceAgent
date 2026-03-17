from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_run import RunStatus, WorkflowRun
from app.schemas.a2a_envelope import A2AMessage
from app.schemas.customer import CustomerBatch


class WorkflowRunRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_pending(
        self,
        message: A2AMessage,
        batch: CustomerBatch,
        workflow_name: str = "customer_behavior_phase1",
    ) -> WorkflowRun:
        run = WorkflowRun(
            message_id=message.message_id,
            correlation_id=message.correlation_id or message.message_id,
            source_agent_id=message.routing.source_agent_id,
            workflow_name=workflow_name,
            skills_requested=["churn_prediction", "sentiment_analysis", "segment_insights"],
            input_batch_id=batch.batch_id,
            input_record_count=batch.count,
            run_config={"priority": message.routing.priority},
            status=RunStatus.PENDING.value,
            agent_version="1.0.0",
        )
        self.db.add(run)
        await self.db.flush()
        return run

    async def mark_running(self, run: WorkflowRun) -> WorkflowRun:
        run.status = RunStatus.RUNNING.value
        run.started_at = datetime.now(timezone.utc)
        await self.db.flush()
        return run

    async def mark_completed(self, run: WorkflowRun, result_summary: dict) -> WorkflowRun:
        finished_at = datetime.now(timezone.utc)
        run.status = RunStatus.COMPLETED.value
        run.completed_at = finished_at
        if run.started_at is not None:
            run.duration_ms = (finished_at - run.started_at).total_seconds() * 1000
        run.result_summary = result_summary
        run.records_succeeded = result_summary.get("records_succeeded", 0)
        run.records_failed = result_summary.get("records_failed", 0)
        await self.db.flush()
        return run

    async def mark_failed(self, run: WorkflowRun, error_detail: str) -> WorkflowRun:
        finished_at = datetime.now(timezone.utc)
        run.status = RunStatus.FAILED.value
        run.completed_at = finished_at
        if run.started_at is not None:
            run.duration_ms = (finished_at - run.started_at).total_seconds() * 1000
        run.error_detail = error_detail
        await self.db.flush()
        return run
