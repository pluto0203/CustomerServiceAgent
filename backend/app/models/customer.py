"""
Customer ORM Model
==================
Bảng lưu trữ CustomerRecord đã được chuẩn hóa từ A2A/CSV/CRM.
Tương ứng với Pydantic schema app/schemas/customer.py.

Thiết kế:
- behavioral_* columns: flat columns cho query nhanh (không JSON) → Churn model dùng trực tiếp.
- feedback_texts: JSONB list of strings → Sentiment pipeline đọc ra xử lý.
- external_ids, extra_attributes: JSONB cho dữ liệu linh hoạt từ upstream.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text

from app.db.base import Base, TimestampMixin


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    # ------------------------------------------------------------------
    # Primary key — UUID để safe khi merge data từ nhiều nguồn
    # ------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    email: Mapped[str | None] = mapped_column(String(320), nullable= True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gender : Mapped[str | None] = mapped_column(String(30), nullable= True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    customer_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Map ID từ hệ thống nguồn: {"hubspot": "123", "zoho": "456"}
    external_ids: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # ------------------------------------------------------------------
    # Behavioral snapshot columns (flat → query index nhanh)
    # Nuôi: Churn Predictor, Segment Skill
    # ------------------------------------------------------------------
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_order_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_order_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    days_since_last_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engagement_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    support_ticket_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_support_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ------------------------------------------------------------------
    # Text feedback (JSONB list)
    # Nuôi: Sentiment Analyzer Skill
    # ------------------------------------------------------------------
    feedback_reviews: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    feedback_tickets: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    feedback_social: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    feedback_surveys: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # ------------------------------------------------------------------
    # Metadata / audit
    # ------------------------------------------------------------------
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    extra_attributes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Batch ID từ A2A envelope (để trace group records cùng nguồn)
    ingestion_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        Index("ix_customers_email_unique", "email", unique=True,postgresql_where=text("email IS NOT NULL")),
        Index("ix_customers_churn_features",
              "days_since_last_order", "total_orders", "support_ticket_count"),
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} email={self.email} source={self.source}>"
