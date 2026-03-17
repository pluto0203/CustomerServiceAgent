"""
A2A Message Envelope — Agent-to-Agent Communication Contract
=============================================================
Đây là lớp bọc ngoài (envelope) cho mọi message trao đổi giữa các agent
trong hệ thống MultiAgentAssistant.

Tại sao cần envelope riêng thay vì gửi thẳng CustomerRecord?
- Mang metadata routing: biết message đến từ agent nào, gửi đến agent nào.
- Mang correlation_id để trace một request qua nhiều agent.
- Cho phép mở rộng payload type mà không phá vỡ contract hiện tại.
- Tách bạch transport layer (envelope) khỏi business layer (payload).

Luồng điển hình:
  DataCollector Agent
      → gửi A2AMessage(payload_type="customer_batch", payload=[...])
      → Customer Behavior Agent nhận, unpack payload, xử lý
      → trả A2AMessage(payload_type="analysis_result", payload={...})
      → Orchestrator nhận kết quả.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class A2APayloadType(str, Enum):
    """Loại payload được phép truyền qua envelope."""

    # Input: các loại dữ liệu module này nhận vào
    CUSTOMER_RECORD = "customer_record"       # Một CustomerRecord đơn
    CUSTOMER_BATCH = "customer_batch"         # CustomerBatch nhiều records
    TRACKING_EVENT = "tracking_event"         # Sự kiện hành vi realtime
    ANALYSIS_REQUEST = "analysis_request"     # Yêu cầu chạy skill cụ thể

    # Output: các loại kết quả module này trả ra
    ANALYSIS_RESULT = "analysis_result"       # Kết quả skill đã chạy xong
    ERROR = "error"                           # Lỗi xử lý


class A2AStatus(str, Enum):
    SUCCESS = "success"
    ACCEPTED = "accepted"     # Nhận được, đang xử lý async
    FAILED = "failed"
    PARTIAL = "partial"       # Một phần record lỗi, phần còn lại thành công


class A2ARoutingInfo(BaseModel):
    """Metadata điều hướng — để orchestrator biết message đi từ đâu đến đâu."""

    source_agent_id: str = Field(
        ...,
        description="ID định danh agent gửi message. Ví dụ: 'data-collector-v1'",
    )
    target_agent_id: str = Field(
        default="customer-behavior-agent",
        description="ID agent nhận message.",
    )
    reply_to: str | None = Field(
        default=None,
        description="Endpoint hoặc agent ID để gửi response về. None = fire-and-forget.",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Độ ưu tiên xử lý. 1 = cao nhất, 10 = thấp nhất.",
    )


class A2AMessage(BaseModel):
    """
    Envelope chuẩn cho mọi message Agent-to-Agent.

    Mọi HTTP request đến /api/v1/agent/input đều phải wrap dữ liệu
    trong A2AMessage này. Module Customer Behavior Agent sẽ:
    1. Validate envelope.
    2. Unpack payload theo payload_type.
    3. Normalize về CustomerRecord/CustomerBatch.
    4. Đẩy vào pipeline phân tích.
    """

    # --- Định danh message ---
    message_id: UUID = Field(
        default_factory=uuid4,
        description="ID duy nhất của message này.",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description=(
            "ID dùng để liên kết nhiều message trong cùng một request flow. "
            "Nếu không có, hệ thống sẽ tự dùng message_id."
        ),
    )

    # --- Routing ---
    routing: A2ARoutingInfo

    # --- Payload ---
    payload_type: A2APayloadType
    payload: Any = Field(
        ...,
        description=(
            "Dữ liệu thực sự. Được parse theo payload_type: "
            "customer_batch -> CustomerBatch, "
            "customer_record -> CustomerRecord, v.v."
        ),
    )

    # --- Control ---
    schema_version: str = Field(default="1.0")
    sent_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"json_schema_extra": {"example": {
        "routing": {
            "source_agent_id": "crm-sync-agent-v1",
            "target_agent_id": "customer-behavior-agent",
            "reply_to": "orchestrator",
            "priority": 3,
        },
        "payload_type": "customer_batch",
        "payload": {
            "batch_id": "550e8400-e29b-41d4-a716-446655440000",
            "source_agent_id": "crm-sync-agent-v1",
            "records": [
                {
                    "external_ids": {"hubspot": "contact_001"},
                    "email": "khach.hang@example.com",
                    "source": "agent_a2a",
                    "behavioral": {"total_orders": 3, "days_since_last_order": 60},
                    "feedback": {"reviews": ["Dich vu can cai thien"]},
                }
            ],
        },
    }}}


# ---------------------------------------------------------------------------
# Response envelope — module này trả về cho orchestrator
# ---------------------------------------------------------------------------


class A2AResponse(BaseModel):
    """Kết quả trả ra từ Customer Behavior Agent sau khi xử lý A2AMessage."""

    message_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID | None = None          # Echo lại từ request
    in_response_to: UUID                        # message_id của request gốc

    status: A2AStatus
    payload_type: A2APayloadType
    payload: Any                                # AnalysisResult hoặc ErrorDetail

    processing_time_ms: float | None = None
    responded_at: datetime = Field(default_factory=datetime.utcnow)
