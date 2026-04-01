from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.skills import ChurnPredictionService, SegmentInsightsService, SentimentAnalysisService

router = APIRouter(prefix="/skills", tags=["Skill Runs"])


class SkillRunRequest(BaseModel):
    customer_ids: list[UUID] | None = Field(
        default=None,
        description="Optional list customer IDs cần chạy skill. Để trống sẽ lấy theo limit.",
    )
    limit: int = Field(default=500, ge=1, le=5000)


@router.post("/churn-prediction/run", summary="Run churn prediction skill")
async def run_churn_prediction(
    request: SkillRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ChurnPredictionService()
    results = await service.analyze_from_db(db, request.customer_ids, request.limit)
    return {
        "skill_name": "churn_prediction",
        "count": len(results),
        "results": results,
    }


@router.post("/sentiment-analysis/run", summary="Run sentiment analysis skill")
async def run_sentiment_analysis(
    request: SkillRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = SentimentAnalysisService()
    results = await service.analyze_from_db(db, request.customer_ids, request.limit)
    return {
        "skill_name": "sentiment_analysis",
        "count": len(results),
        "results": results,
    }


@router.post("/segment-insights/run", summary="Run segment insights skill")
async def run_segment_insights(
    request: SkillRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = SegmentInsightsService()
    results = await service.analyze_from_db(db, request.customer_ids, request.limit)
    return {
        "skill_name": "segment_insights",
        "count": len(results),
        "results": results,
    }
