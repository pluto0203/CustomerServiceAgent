"""
WorkflowRun ORM Model
=====================
Mỗi lần một workflow (tập các Skills) được trigger đều tạo một WorkflowRun.
Đây là đơn vị tracking/audit chính cho Phase 1.

Lifecycle:
    PENDING → RUNNING → COMPLETED | FAILED | CANCELLED
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"        # Một số records thành công, một số lỗi


class WorkflowRun(TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ------------------------------------------------------------------
    # Liên kết với A2A message gốc (để trace từ run ngược về message)
    # ------------------------------------------------------------------
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source_agent_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ------------------------------------------------------------------
    # Workflow definition & config
    # ------------------------------------------------------------------
    # Tên workflow hoặc list skills chạy: ["churn", "sentiment", "segment"]
    workflow_name: Mapped[str] = mapped_column(String(200), nullable=False)
    skills_requested: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    run_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # ------------------------------------------------------------------
    # Input summary
    # ------------------------------------------------------------------
    input_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    input_record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ------------------------------------------------------------------
    # Execution state
    # ------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        String(50),
        default=RunStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ------------------------------------------------------------------
    # Results & errors
    # ------------------------------------------------------------------
    # Summary của toàn bộ run (không phải per-record result)
    result_summary: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    records_succeeded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ------------------------------------------------------------------
    # Versioning — để audit và reproduce
    # ------------------------------------------------------------------
    model_versions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    prompt_versions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)

    __table_args__ = (
        Index("ix_workflow_runs_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<WorkflowRun id={self.id} workflow={self.workflow_name} "
            f"status={self.status}>"
        )
