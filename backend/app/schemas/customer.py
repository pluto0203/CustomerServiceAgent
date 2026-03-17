"""
Canonical Customer Schema v1
============================
Đây là hợp đồng dữ liệu cốt lõi (data contract) của toàn hệ thống.

Mọi nguồn đầu vào (A2A JSON, CSV, CRM connector) đều phải được
map về CustomerRecord trước khi Agent Skills đụng vào.

Nguyên tắc thiết kế:
- Strict typing với Pydantic v2 để phát hiện lỗi sớm tại cổng vào.
- Tất cả field nghiệp vụ là Optional để hệ thống chịu được dữ liệu thiếu.
- external_ids lưu ID gốc từ hệ thống upstream để trace và deduplicate.
- behavioral_snapshot và text_feedback là 2 nhóm chính nuôi 3 Skills.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, field_validator


class DataSource(str, Enum):
    """Nguồn gốc của bản ghi — dùng để audit và route xử lý."""

    AGENT_A2A = "agent_a2a"       # JSON từ agent upstream (ưu tiên)
    WEBHOOK = "webhook"           # Tracking event realtime
    CSV_UPLOAD = "csv_upload"     # Upload thủ công / test
    CRM_SYS = "CRM_system"


# ---------------------------------------------------------------------------
# Sub-models — nhóm field theo nghiệp vụ để dễ mở rộng từng nhóm độc lập
# ---------------------------------------------------------------------------


class BehavioralSnapshot(BaseModel):
    """
    Hành vi tổng hợp của khách hàng — nuôi Churn Predictor và Segment Skill.
    Tất cả giá trị là kết quả tổng hợp (aggregate), không phải raw event.
    """

    total_orders: int = Field(default=0, ge=0)
    total_revenue: float = Field(default=0.0, ge=0.0)
    avg_order_value: float | None = Field(default=None, ge=0.0)
    last_order_at: datetime | None = None

    # Tính từ last_order_at — agent upstream hoặc pipeline tự tính
    days_since_last_order: int | None = Field(default=None, ge=0)

    # Tỉ lệ tương tác: email open rate, click rate, app session count...
    engagement_score: float | None = Field(default=None, ge=0.0, le=1.0)
    support_ticket_count: int = Field(default=0, ge=0)
    last_support_at: datetime | None = None


class TextFeedback(BaseModel):
    """
    Nội dung text thô từ khách hàng — nuôi Sentiment Analyzer Skill.
    Có thể có nhiều review; lưu list để analyzer xử lý batch.
    """

    reviews: list[str] = Field(default_factory=list)
    support_tickets: list[str] = Field(default_factory=list)
    social_comments: list[str] = Field(default_factory=list)
    survey_responses: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Canonical Customer Record — root entity của toàn hệ thống
# ---------------------------------------------------------------------------


class CustomerRecord(BaseModel):
    """
    Bản ghi khách hàng chuẩn hóa (Canonical Customer Record).

    Đây là đơn vị dữ liệu duy nhất mà tất cả Skills nhận vào.
    Cho dù dữ liệu đến từ A2A JSON, CSV hay CRM, sau khi qua
    ingestion layer thì đều phải được biểu diễn bằng model này.
    """

    # --- Định danh ---
    customer_id: UUID = Field(
        default_factory=uuid4,
        description="ID nội bộ hệ thống. Nếu upstream chưa có thì tự sinh.",
    )
    external_ids: dict[str, str] = Field(
        default_factory=dict,
        description='Map ID từ hệ thống gốc. Ví dụ: {"hubspot": "123", "zoho": "456"}',
    )

    # --- Thông tin cơ bản ---
    email: EmailStr | None = None
    phone: str | None = None
    full_name: str | None = None
    gender: str | None = None
    customer_created_at: datetime | None = None
    created_at: datetime | None = None

    # --- Hành vi tổng hợp ---
    behavioral: BehavioralSnapshot = Field(default_factory=BehavioralSnapshot)

    # --- Phản hồi / text ---
    feedback: TextFeedback = Field(default_factory=TextFeedback)

    # --- Custom attributes từ upstream agent ---
    # Dùng cho các field đặc thù ngành chưa được chuẩn hóa vào schema
    extra_attributes: dict[str, Any] = Field(default_factory=dict)

    # --- Metadata nguồn gốc — bắt buộc để audit ---
    source: DataSource
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

    # --- Versioning schema để phát hiện lệch contract ---
    schema_version: str = Field(default="1.0")

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: str | None) -> str | None:
        """Loại bỏ ký tự không phải số, giữ dấu + ở đầu."""
        if v is None:
            return None
        cleaned = "".join(c for c in v if c.isdigit() or c == "+")
        return cleaned or None

    model_config = {"json_schema_extra": {"example": {
        "external_ids": {"hubspot": "contact_789"},
        "email": "nguyen.van.a@example.com",
        "full_name": "Nguyen Van A",
        "gender": "male",
        "source": "agent_a2a",
        "behavioral": {
            "total_orders": 5,
            "total_revenue": 2500000,
            "days_since_last_order": 45,
            "support_ticket_count": 2,
        },
        "feedback": {
            "reviews": ["San pham tot nhung giao hang cham"],
            "support_tickets": ["Chua nhan duoc hang sau 7 ngay"],
        },
    }}}


# ---------------------------------------------------------------------------
# Batch wrapper — dùng khi A2A hoặc ingestion gửi nhiều records cùng lúc
# ---------------------------------------------------------------------------


class CustomerBatch(BaseModel):
    """Batch nhiều CustomerRecord trong một lần gửi từ agent upstream."""

    records: list[CustomerRecord] = Field(..., min_length=1)
    batch_id: UUID = Field(default_factory=uuid4)
    source_agent_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def count(self) -> int:
        return len(self.records)
