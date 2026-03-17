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

import time
from uuid import uuid4

from fastapi import BackgroundTasks

from app.schemas.a2a_envelope import (
    A2AMessage,
    A2APayloadType,
    A2AResponse,
    A2AStatus,
)
from app.schemas.customer import CustomerBatch, CustomerRecord, DataSource


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

    async def accept_async(
        self,
        message: A2AMessage,
        background_tasks: BackgroundTasks,
    ) -> A2AResponse:
        """
        Nhận message, validate, enqueue background job, trả 202 ngay.
        Đây là happy path chính cho production.
        """
        self._validate_payload_type(message)

        # Idempotency: TODO Sprint 2 — check DB xem message_id đã xử lý chưa

        # Enqueue — TODO Sprint 2: thay bằng Celery task thật
        job_id = str(uuid4())
        background_tasks.add_task(self._process_in_background, message, job_id)

        return A2AResponse(
            correlation_id=message.correlation_id or message.message_id,
            in_response_to=message.message_id,
            status=A2AStatus.ACCEPTED,
            payload_type=A2APayloadType.ANALYSIS_REQUEST,
            payload={
                "job_id": job_id,
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

        start = time.perf_counter()
        batch = self._unpack_to_batch(message)
        result = await self._run_analysis_pipeline(batch)
        elapsed_ms = (time.perf_counter() - start) * 1000

        return A2AResponse(
            correlation_id=message.correlation_id or message.message_id,
            in_response_to=message.message_id,
            status=A2AStatus.SUCCESS,
            payload_type=A2APayloadType.ANALYSIS_RESULT,
            payload=result,
            processing_time_ms=elapsed_ms,
        )

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def _validate_payload_type(self, message: A2AMessage) -> None:
        """Kiểm tra payload_type có phải loại module này xử lý không."""
        accepted = {
            A2APayloadType.CUSTOMER_RECORD,
            A2APayloadType.CUSTOMER_BATCH,
            A2APayloadType.TRACKING_EVENT,
            A2APayloadType.ANALYSIS_REQUEST,
        }
        if message.payload_type not in accepted:
            raise ValueError(
                f"payload_type '{message.payload_type}' không được hỗ trợ. "
                f"Chấp nhận: {[t.value for t in accepted]}"
            )

    def _unpack_to_batch(self, message: A2AMessage) -> CustomerBatch:
        """
        Unpack payload từ A2AMessage về CustomerBatch chuẩn.

        Dù agent gửi 1 record hay nhiều records, đầu ra luôn là CustomerBatch
        để pipeline phân tích chỉ cần xử lý một kiểu input duy nhất.
        """
        payload = message.payload

        if message.payload_type == A2APayloadType.CUSTOMER_BATCH:
            if isinstance(payload, CustomerBatch):
                return payload
            # Nếu payload là raw dict (JSON vừa deserialize)
            return CustomerBatch.model_validate(payload)

        if message.payload_type == A2APayloadType.CUSTOMER_RECORD:
            if isinstance(payload, CustomerRecord):
                record = payload
            else:
                record = CustomerRecord.model_validate(payload)
            return CustomerBatch(
                records=[record],
                source_agent_id=message.routing.source_agent_id,
            )

        if message.payload_type == A2APayloadType.TRACKING_EVENT:
            # TODO Sprint 3: convert tracking event → CustomerRecord
            # Hiện tại tạo placeholder record từ event data
            record = CustomerRecord(
                source=DataSource.WEBHOOK,
                extra_attributes=payload if isinstance(payload, dict) else {},
            )
            return CustomerBatch(
                records=[record],
                source_agent_id=message.routing.source_agent_id,
            )

        # ANALYSIS_REQUEST: payload chứa customer_ids + skill config
        # TODO Sprint 2: load records từ DB theo customer_ids trong payload
        raise NotImplementedError(
            "ANALYSIS_REQUEST payload type sẽ implement ở Sprint 2 "
            "khi có CustomerRepository."
        )

    async def _run_analysis_pipeline(self, batch: CustomerBatch) -> dict:
        """
        Chạy toàn bộ pipeline phân tích cho một CustomerBatch.

        TODO Sprint 3-5: thay stub này bằng LangGraph orchestrator thật:
            orchestrator = AgentOrchestrator()
            return await orchestrator.run(batch, skills=["churn", "sentiment", "segment"])
        """
        # Stub trả về mock result để endpoint có thể test end-to-end ngay
        return {
            "batch_id": str(batch.batch_id),
            "record_count": batch.count,
            "results": [
                {
                    "customer_id": str(r.customer_id),
                    "churn_risk": None,         # TODO: ChurnSkill
                    "sentiment": None,          # TODO: SentimentSkill
                    "segment": None,            # TODO: SegmentSkill
                    "status": "pending_implementation",
                }
                for r in batch.records
            ],
            "note": "Stub result — skills sẽ implement từ Sprint 3.",
        }

    async def _process_in_background(self, message: A2AMessage, job_id: str) -> None:
        """
        Background task placeholder. Sprint 2 sẽ thay bằng Celery task.

        Celery task sẽ:
        1. Persist batch vào Postgres.
        2. Index text feedback vào Qdrant.
        3. Chạy skills pipeline.
        4. Persist kết quả.
        5. Callback reply_to nếu có.
        """
        # TODO Sprint 2: celery_app.send_task("tasks.process_a2a_message", ...)
        batch = self._unpack_to_batch(message)
        await self._run_analysis_pipeline(batch)
