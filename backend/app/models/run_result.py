"""
RunResult ORM Model
===================
Lưu kết quả phân tích ở cấp độ từng customer record trong một WorkflowRun.

1 WorkflowRun  →  N RunResult (1 per customer per skill)

Thiết kế tách biệt kết quả theo skill_name để:
- Query kết quả churn riêng, sentiment riêng mà không cần unpack JSON lớn.
- Dễ re-run 1 skill mà không ảnh hưởng kết quả skill khác.
- Dễ export report theo skill.
"""

import uuid

from sqlalchemy import Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RunResult(TimestampMixin, Base):
    __tablename__ = "run_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ------------------------------------------------------------------
    # Foreign keys (không dùng FK constraint để tránh lock phức tạp ở MVP)
    # Validate tính toàn vẹn ở application layer.
    # ------------------------------------------------------------------
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # ------------------------------------------------------------------
    # Skill identification
    # ------------------------------------------------------------------
    # "churn_prediction" | "sentiment_analysis" | "segment_insights"
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)

    # ------------------------------------------------------------------
    # Core result fields (flat cho query nhanh)
    # ------------------------------------------------------------------
    # Churn: probability 0.0–1.0, Sentiment: score -1.0–1.0, Segment: cluster id
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Human-readable summary (LLM generated hoặc template)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ------------------------------------------------------------------
    # Detailed output — full result object của skill
    # ------------------------------------------------------------------
    # Churn: {"score": 0.82, "top_factors": [...], "recommended_action": "..."}
    # Sentiment: {"label": "negative", "topics": [...], "trend": "..."}
    # Segment: {"cluster_id": 3, "cluster_name": "At-risk VIP", "insights": [...]}
    result_detail: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Explainability: top features hoặc evidence dùng để tạo ra kết quả
    explainability: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # ------------------------------------------------------------------
    # Processing metadata
    # ------------------------------------------------------------------
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_run_results_run_skill", "workflow_run_id", "skill_name"),
        Index("ix_run_results_customer_skill", "customer_id", "skill_name"),
        Index("ix_run_results_score_label", "skill_name", "score", "label"),
    )

    def __repr__(self) -> str:
        return (
            f"<RunResult customer={self.customer_id} skill={self.skill_name} "
            f"score={self.score} label={self.label}>"
        )
