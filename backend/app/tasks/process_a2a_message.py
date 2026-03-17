from __future__ import annotations

import asyncio

from celery import shared_task

from app.schemas.a2a_envelope import A2AMessage
from app.services.agent.processing_service import process_message_timed


@shared_task(name="app.tasks.process_a2a_message.process_a2a_message")
def process_a2a_message(message_payload: dict) -> dict:
    message = A2AMessage.model_validate(message_payload)
    result, processing_time_ms = asyncio.run(process_message_timed(message))
    return {
        **result,
        "processing_time_ms": processing_time_ms,
    }
