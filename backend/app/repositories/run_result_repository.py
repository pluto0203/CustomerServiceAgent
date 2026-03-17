from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run_result import RunResult


class RunResultRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_many(self, workflow_run_id: UUID, results: list[dict[str, Any]]) -> list[RunResult]:
        created: list[RunResult] = []
        for item in results:
            result = RunResult(
                workflow_run_id=workflow_run_id,
                customer_id=item["customer_id"],
                skill_name=item["skill_name"],
                skill_version=item.get("skill_version", "1.0"),
                score=item.get("score"),
                label=item.get("label"),
                confidence=item.get("confidence"),
                summary=item.get("summary"),
                result_detail=item.get("result_detail", {}),
                explainability=item.get("explainability", {}),
                model_version=item.get("model_version"),
                prompt_version=item.get("prompt_version"),
                processing_ms=item.get("processing_ms"),
                error_detail=item.get("error_detail"),
            )
            self.db.add(result)
            created.append(result)

        await self.db.flush()
        return created
