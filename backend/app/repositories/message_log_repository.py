from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message_log import MessageLog
from app.schemas.a2a_envelope import A2AMessage


class MessageLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_message_id(self, message_id: UUID) -> MessageLog | None:
        stmt = select(MessageLog).where(MessageLog.message_id == message_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_received(self, message: A2AMessage) -> MessageLog:
        existing = await self.get_by_message_id(message.message_id)
        if existing is not None:
            return existing

        log = MessageLog(
            message_id=message.message_id,
            correlation_id=message.correlation_id or message.message_id,
            source_agent_id=message.routing.source_agent_id,
            target_agent_id=message.routing.target_agent_id,
            payload_type=message.payload_type.value,
            status="received",
            sent_at=message.sent_at,
            raw_payload=message.model_dump(mode="json"),
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def mark_accepted(self, message_id: UUID, celery_task_id: str) -> MessageLog | None:
        log = await self.get_by_message_id(message_id)
        if log is None:
            return None
        log.status = "accepted"
        log.celery_task_id = celery_task_id
        log.accepted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return log

    async def mark_processing(self, message_id: UUID) -> MessageLog | None:
        log = await self.get_by_message_id(message_id)
        if log is None:
            return None
        log.status = "processing"
        await self.db.flush()
        return log

    async def mark_completed(self, message_id: UUID, workflow_run_id: UUID) -> MessageLog | None:
        log = await self.get_by_message_id(message_id)
        if log is None:
            return None
        log.status = "completed"
        log.workflow_run_id = workflow_run_id
        log.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return log

    async def mark_failed(self, message_id: UUID, error_detail: str) -> MessageLog | None:
        log = await self.get_by_message_id(message_id)
        if log is None:
            return None
        log.status = "failed"
        log.error_detail = error_detail
        log.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return log
