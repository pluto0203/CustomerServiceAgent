"""
Agent Input Endpoint
====================
Cổng vào chính của module Customer Behavior Agent khi hoạt động
trong hệ thống MultiAgentAssistant.

Có 2 mode nhận dữ liệu:
- POST /agent/input      : Nhận A2AMessage chuẩn từ agent upstream.
                           Xử lý async (Celery job), trả về accepted ngay.
- POST /agent/input/sync : Nhận A2AMessage, xử lý sync, trả kết quả liền.
                           Chỉ dùng cho batch nhỏ (<= 100 records) hoặc test.

Fallback (test/manual):
- POST /agent/ingest/csv : Upload CSV trực tiếp (không qua A2A envelope).
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status

from app.schemas.a2a_envelope import A2AMessage, A2AResponse, A2AStatus, A2APayloadType
from app.services.agent.message_handler import AgentMessageHandler

router = APIRouter(prefix="/agent", tags=["Agent Input"])

# ---------------------------------------------------------------------------
# Dependency injection placeholder — sẽ implement đầy đủ ở Sprint 1
# ---------------------------------------------------------------------------


def get_message_handler() -> AgentMessageHandler:
    return AgentMessageHandler()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/input",
    response_model=A2AResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Nhận A2A message từ agent upstream (async)",
    description=(
        "Endpoint chính để các agent khác trong MultiAgentAssistant gửi dữ liệu "
        "khách hàng vào module này. Trả về 202 Accepted ngay, kết quả xử lý được "
        "gửi lại qua routing.reply_to hoặc lưu vào run results."
    ),
)
async def receive_agent_message(
    message: A2AMessage,
    background_tasks: BackgroundTasks,
    handler: AgentMessageHandler = Depends(get_message_handler),
) -> A2AResponse:
    """
    Nhận A2AMessage, validate, enqueue Celery job, trả 202 ngay.

    Flow:
    1. Validate envelope và payload_type.
    2. Ghi nhận message vào DB (idempotency check qua message_id).
    3. Enqueue Celery task theo payload_type.
    4. Trả A2AResponse(status=accepted) với job_id trong payload.
    """
    try:
        response = await handler.accept_async(message, background_tasks)
        return response
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/input/sync",
    response_model=A2AResponse,
    status_code=status.HTTP_200_OK,
    summary="Nhận A2A message và xử lý đồng bộ (sync — chỉ dùng cho batch nhỏ)",
    description=(
        "Xử lý ngay trong request, trả kết quả phân tích liền. "
        "Chỉ dùng khi batch <= 100 records. Quá giới hạn sẽ trả 413."
    ),
)
async def receive_agent_message_sync(
    message: A2AMessage,
    handler: AgentMessageHandler = Depends(get_message_handler),
) -> A2AResponse:
    """
    Nhận A2AMessage, xử lý ngay (blocking), trả kết quả trong response.
    Phù hợp cho: test, demo, trigger từ orchestrator cần kết quả liền.
    """
    # Giới hạn batch size để tránh timeout HTTP
    if message.payload_type == A2APayloadType.CUSTOMER_BATCH:
        batch = message.payload
        record_count = len(batch.get("records", [])) if isinstance(batch, dict) else 0
        if record_count > 100:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"Sync mode chỉ xử lý tối đa 100 records, "
                    f"nhận {record_count}. Dùng /agent/input (async) thay thế."
                ),
            )

    try:
        response = await handler.process_sync(message)
        return response
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/input/status/{message_id}",
    summary="Kiểm tra trạng thái xử lý của một A2A message",
)
async def get_message_status(
    message_id: UUID,
    handler: AgentMessageHandler = Depends(get_message_handler),
) -> dict:
    """
    Trả trạng thái và kết quả (nếu có) của message đã gửi vào /agent/input.
    Dùng cho agent upstream poll kết quả khi không có reply_to callback.
    """
    # TODO Sprint 2: truy vấn run_results từ DB theo message_id
    return {
        "message_id": str(message_id),
        "status": "not_implemented",
        "note": "Sẽ implement ở Sprint 2 khi có run_results table.",
    }


@router.post(
    "/ingest/csv",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload CSV trực tiếp (fallback / manual testing)",
    description=(
        "Không đi qua A2A envelope. Dùng khi không có agent upstream "
        "hoặc khi test thủ công với file dữ liệu mẫu."
    ),
)
async def ingest_csv(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    handler: AgentMessageHandler = Depends(get_message_handler),
) -> dict:
    """
    Nhận file CSV, validate format, enqueue ingestion job.
    CSV phải có ít nhất 1 trong các cột: email, phone, customer_id.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Chỉ chấp nhận file .csv",
        )

    # TODO Sprint 2: đọc CSV, validate, wrap thành CustomerBatch, enqueue
    return {
        "status": "accepted",
        "filename": file.filename,
        "note": "CSV ingestion sẽ implement đầy đủ ở Sprint 2.",
    }
