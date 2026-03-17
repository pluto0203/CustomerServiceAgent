"""
Agent Message Handler
=====================
Service trung tâm xử lý A2AMessage nhận từ agent upstream.

Trách nhiệm:
1. Validate payload theo payload_type.
2. Normalize payload về CustomerRecord / CustomerBatch.
3. Route sang đúng pipeline (enqueue Celery job hoặc xử lý sync).
4. Build và trả A2AResponse chuẩn.

Không chứa business logic phân tích — chỉ là orchestration layer.
Business logic nằm trong app/skills/ và app/services/agent/orchestrator.py.
"""

from __future__ import annotations

from uuid import UUID

from app.db.session import async_session
from app.repositories import MessageLogRepository

from app.schemas.a2a_envelope import (
    A2AMessage,
    A2APayloadType,
    A2AResponse,
    A2AStatus,
)
from app.services.agent.processing_service import AgentProcessingService, process_message_timed
from app.tasks.celery_app import celery_app


class AgentMessageHandler:
    """
    Handler chính cho A2A messages.

    Sử dụng qua dependency injection trong endpoint:
        handler = AgentMessageHandler()
        response = await handler.accept_async(message, background_tasks)
    """

    # ---------------------------------------------------------------------------
    # Public interface
    # ---------------------------------------------------------------------------

    def __init__(self) -> None:
        self.processing_service = AgentProcessingService()

    async def accept_async(self, message: A2AMessage) -> A2AResponse:
        """
        Nhận message, validate, enqueue background job, trả 202 ngay.
        Đây là happy path chính cho production.
        """
        self._validate_payload_type(message)

        async with async_session() as db:
            logs = MessageLogRepository(db)
            existing = await logs.get_by_message_id(message.message_id)
            if existing is not None:
                return A2AResponse(
                    correlation_id=message.correlation_id or message.message_id,
                    in_response_to=message.message_id,
                    status=A2AStatus.ACCEPTED,
                    payload_type=A2APayloadType.ANALYSIS_REQUEST,
                    payload={
                        "job_id": existing.celery_task_id,
                        "message": "Message đã tồn tại, trả về trạng thái enqueue hiện có.",
                    },
                )

            await logs.create_received(message)
            async_result = celery_app.send_task(
                "app.tasks.process_a2a_message.process_a2a_message",
                kwargs={"message_payload": message.model_dump(mode="json")},
            )
            await logs.mark_accepted(message.message_id, async_result.id)
            await db.commit()

        return A2AResponse(
            correlation_id=message.correlation_id or message.message_id,
            in_response_to=message.message_id,
            status=A2AStatus.ACCEPTED,
            payload_type=A2APayloadType.ANALYSIS_REQUEST,
            payload={
                "job_id": async_result.id,
                "message": (
                    f"Đã nhận {message.payload_type.value}, "
                    f"đang xử lý. Poll /agent/input/status/{message.message_id} "
                    f"để lấy kết quả."
                ),
            },
        )

    async def process_sync(self, message: A2AMessage) -> A2AResponse:
        """
        Xử lý ngay trong request, trả kết quả phân tích liền.
        Dùng cho batch nhỏ hoặc test.
        """
        self._validate_payload_type(message)

        result, elapsed_ms = await process_message_timed(message)

        return A2AResponse(
            correlation_id=message.correlation_id or message.message_id,
            in_response_to=message.message_id,
            status=A2AStatus.SUCCESS,
            payload_type=A2APayloadType.ANALYSIS_RESULT,
            payload=result,
            processing_time_ms=elapsed_ms,
        )

    async def get_status(self, message_id: UUID) -> dict:
        return await self.processing_service.get_message_status(message_id)

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def _validate_payload_type(self, message: A2AMessage) -> None:
        """Kiểm tra payload_type có phải loại module này xử lý không."""
        accepted = {
            A2APayloadType.CUSTOMER_RECORD,
            A2APayloadType.CUSTOMER_BATCH,
            A2APayloadType.TRACKING_EVENT,
        }
        if message.payload_type not in accepted:
            raise ValueError(
                f"payload_type '{message.payload_type}' không được hỗ trợ. "
                f"Chấp nhận: {[t.value for t in accepted]}"
            )
