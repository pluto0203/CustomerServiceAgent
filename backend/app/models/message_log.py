"""
MessageLog ORM Model
====================
Ghi lại mọi A2AMessage nhận vào để phục vụ 2 mục đích:
1. Idempotency: kiểm tra message_id đã xử lý chưa trước khi enqueue lại.
2. Audit trail: trace toàn bộ luồng message trong hệ thống MultiAgent.

Retention policy: log được giữ 90 ngày mặc định (cleanup job ở Phase 2).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MessageLog(TimestampMixin, Base):
    __tablename__ = "message_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ------------------------------------------------------------------
    # A2A Envelope fields (denormalized để query nhanh)
    # ------------------------------------------------------------------
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,        # Đảm bảo idempotency: 1 message_id chỉ xử lý 1 lần
        index=True,
    )
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    source_agent_id: Mapped[str] = mapped_column(String(200), nullable=False)
    target_agent_id: Mapped[str] = mapped_column(String(200), nullable=False)
    payload_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # ------------------------------------------------------------------
    # Processing state
    # ------------------------------------------------------------------
    # "received" | "accepted" | "processing" | "completed" | "failed"
    status: Mapped[str] = mapped_column(String(50), default="received", nullable=False)

    # Job ID trong Celery (để cancel hoặc track)
    celery_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # WorkflowRun được tạo từ message này
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ------------------------------------------------------------------
    # Raw payload (lưu để debug hoặc replay)
    # Max size: giới hạn ở application layer trước khi ghi vào đây
    # ------------------------------------------------------------------
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_message_logs_correlation", "correlation_id", "status"),
        Index("ix_message_logs_source_agent", "source_agent_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<MessageLog message_id={self.message_id} "
            f"type={self.payload_type} status={self.status}>"
        )
