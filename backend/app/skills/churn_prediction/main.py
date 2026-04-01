from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.services.llm import LLMService


@dataclass(slots=True)
class ChurnPrediction:
    customer_id: UUID
    risk_level: str
    score: float
    confidence: float
    summary: str
    recommended_actions: list[str]
    top_factors: list[str]
    metrics: dict[str, Any]


class ChurnPredictionService:
    skill_name = "churn_prediction"
    skill_version = "1.0"

    def __init__(
        self,
        instruction_path: Path | None = None,
        schema_path: Path | None = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent
        self.instruction_path = instruction_path or (base_dir / "instruction.md")
        self.schema_path = schema_path or (base_dir / "schema.json")
        self._instruction_text = self.instruction_path.read_text(encoding="utf-8")
        self._response_schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self._llm_service = LLMService(skill_name=self.skill_name)

    async def analyze_from_db(
        self,
        db: AsyncSession,
        customer_ids: list[UUID] | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        stmt = select(Customer)
        if customer_ids:
            stmt = stmt.where(Customer.id.in_(customer_ids))
        stmt = stmt.limit(limit)

        rows = await db.execute(stmt)
        customers = list(rows.scalars().all())
        return self.analyze_many(customers)

    def analyze_many(self, customers: list[Customer]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for customer in customers:
            ai_result = self._call_ai(customer)
            prediction = self._from_ai_or_rules(customer, ai_result)
            results.append(self._to_run_result(prediction))
        return results

    def _call_ai(self, customer: Customer) -> dict[str, Any] | None:
        return self._llm_service.generate_json(
            instruction_text=self._instruction_text,
            response_schema=self._response_schema,
            customer_payload=self._build_customer_payload(customer),
            temperature=0.1,
        )

    def _from_ai_or_rules(
        self,
        customer: Customer,
        ai_result: dict[str, Any] | None,
    ) -> ChurnPrediction:
        if ai_result is not None and self._looks_like_valid_result(ai_result):
            return ChurnPrediction(
                customer_id=customer.id,
                risk_level=str(ai_result["risk_level"]),
                score=float(ai_result["score"]),
                confidence=float(ai_result["confidence"]),
                summary=str(ai_result["summary"]),
                recommended_actions=[str(item) for item in ai_result.get("recommended_actions", [])],
                top_factors=[str(item) for item in ai_result.get("top_factors", [])],
                metrics=dict(ai_result.get("metrics", {})),
            )

        return self._rule_based_prediction(customer)

    def _build_customer_payload(self, customer: Customer) -> dict[str, Any]:
        return {
            "customer_id": str(customer.id),
            "total_orders": customer.total_orders or 0,
            "total_revenue": customer.total_revenue or 0.0,
            "days_since_last_order": customer.days_since_last_order,
            "engagement_score": customer.engagement_score,
            "support_ticket_count": customer.support_ticket_count or 0,
            "feedback_reviews_count": len(customer.feedback_reviews or []),
            "feedback_tickets_count": len(customer.feedback_tickets or []),
            "feedback_social_count": len(customer.feedback_social or []),
            "feedback_surveys_count": len(customer.feedback_surveys or []),
        }

    def _looks_like_valid_result(self, result: dict[str, Any]) -> bool:
        required = {
            "risk_level",
            "score",
            "confidence",
            "summary",
            "recommended_actions",
            "top_factors",
            "metrics",
        }
        return required.issubset(result.keys())

    def _rule_based_prediction(self, customer: Customer) -> ChurnPrediction:
        total_orders = customer.total_orders or 0
        total_revenue = customer.total_revenue or 0.0
        days_since_last_order = customer.days_since_last_order
        engagement_score = customer.engagement_score
        support_ticket_count = customer.support_ticket_count or 0

        score = 0.18
        top_factors: list[str] = []

        if days_since_last_order is None:
            top_factors.append("Thieu du lieu recency nen do tin cay giam")
            score += 0.05
        elif days_since_last_order >= 150:
            score += 0.42
            top_factors.append(f"{days_since_last_order} ngay khong mua lai")
        elif days_since_last_order >= 90:
            score += 0.32
            top_factors.append(f"{days_since_last_order} ngay tu lan mua cuoi")
        elif days_since_last_order >= 60:
            score += 0.22
            top_factors.append(f"Recency suy giam: {days_since_last_order} ngay")
        elif days_since_last_order >= 30:
            score += 0.1
        elif days_since_last_order <= 14:
            score -= 0.08
            top_factors.append("Vua mua hang gan day")

        if engagement_score is None:
            top_factors.append("Chua co engagement score day du")
        elif engagement_score < 0.2:
            score += 0.22
            top_factors.append(f"Engagement rat thap ({engagement_score:.2f})")
        elif engagement_score < 0.4:
            score += 0.14
            top_factors.append(f"Engagement giam ({engagement_score:.2f})")
        elif engagement_score < 0.6:
            score += 0.05
        elif engagement_score >= 0.75:
            score -= 0.08
            top_factors.append(f"Engagement tot ({engagement_score:.2f})")

        if support_ticket_count >= 5:
            score += 0.18
            top_factors.append(f"{support_ticket_count} ticket ho tro cho thay friction cao")
        elif support_ticket_count >= 3:
            score += 0.12
            top_factors.append(f"{support_ticket_count} ticket ho tro can follow-up")
        elif support_ticket_count >= 1:
            score += 0.04

        if total_orders <= 1:
            score += 0.1
            top_factors.append("Lich su mua hang con mong")
        elif total_orders >= 8:
            score -= 0.08
            top_factors.append("Da co lich su mua lap lai manh")
        elif total_orders >= 4:
            score -= 0.03

        if total_revenue >= 8_000_000 and days_since_last_order is not None and days_since_last_order >= 90:
            score += 0.07
            top_factors.append("Khach hang gia tri cao dang co dau hieu roi bo")
        elif total_revenue >= 10_000_000 and days_since_last_order is not None and days_since_last_order <= 30:
            score -= 0.05

        score = max(0.02, min(score, 0.98))
        confidence = self._build_confidence(customer)
        risk_level = self._risk_level_from_score(score)
        recommended_actions = self._recommended_actions(risk_level)
        summary = self._build_summary(risk_level, score, days_since_last_order, engagement_score)

        return ChurnPrediction(
            customer_id=customer.id,
            risk_level=risk_level,
            score=round(score, 4),
            confidence=confidence,
            summary=summary,
            recommended_actions=recommended_actions,
            top_factors=top_factors[:5],
            metrics={
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "days_since_last_order": days_since_last_order,
                "engagement_score": engagement_score,
                "support_ticket_count": support_ticket_count,
            },
        )

    def _build_confidence(self, customer: Customer) -> float:
        present_signals = 0
        for value in (
            customer.total_orders,
            customer.total_revenue,
            customer.days_since_last_order,
            customer.engagement_score,
            customer.support_ticket_count,
        ):
            if value is not None:
                present_signals += 1
        confidence = 0.45 + (present_signals / 5) * 0.45
        feedback_volume = sum(
            len(items or [])
            for items in (
                customer.feedback_reviews,
                customer.feedback_tickets,
                customer.feedback_social,
                customer.feedback_surveys,
            )
        )
        if feedback_volume > 0:
            confidence += 0.05
        return round(min(confidence, 0.95), 4)

    def _risk_level_from_score(self, score: float) -> str:
        if score >= 0.8:
            return "critical"
        if score >= 0.62:
            return "high"
        if score >= 0.4:
            return "medium"
        if score >= 0.22:
            return "low"
        return "stable"

    def _recommended_actions(self, risk_level: str) -> list[str]:
        if risk_level == "critical":
            return [
                "CSKH senior lien he truc tiep trong 24h de xu ly friction va giu chan",
                "Kich hoat win-back offer ca nhan hoa gan voi van de khach da gap",
            ]
        if risk_level == "high":
            return [
                "Chay retention journey da kenh trong 7 ngay toi",
                "Ra soat ticket mo va dong vong phan hoi voi khach hang",
            ]
        if risk_level == "medium":
            return [
                "Nuoi duong lai engagement bang campaign use-case va uu dai nhe",
                "Theo doi sat recency va tang tan suat cham soc neu tiep tuc giam",
            ]
        if risk_level == "low":
            return [
                "Duy tri touchpoint dinh ky de tranh giam tuong tac",
                "Kiem tra co hoi cross-sell hoac loyalty nhe",
            ]
        return [
            "Duy tri trai nghiem on dinh va tiep tuc nuoi loyalty",
            "Theo doi som neu recency hoac engagement xau di",
        ]

    def _build_summary(
        self,
        risk_level: str,
        score: float,
        days_since_last_order: int | None,
        engagement_score: float | None,
    ) -> str:
        recency_text = (
            f"{days_since_last_order} ngay tu lan mua cuoi"
            if days_since_last_order is not None
            else "thieu thong tin recency"
        )
        engagement_text = (
            f"engagement {engagement_score:.2f}"
            if engagement_score is not None
            else "thieu engagement score"
        )
        return (
            f"Rui ro churn o muc {risk_level} voi xac suat {score:.0%}; "
            f"{recency_text}, {engagement_text}."
        )

    def _to_run_result(self, prediction: ChurnPrediction) -> dict[str, Any]:
        return {
            "customer_id": prediction.customer_id,
            "skill_name": self.skill_name,
            "skill_version": self.skill_version,
            "score": prediction.score,
            "label": prediction.risk_level,
            "confidence": prediction.confidence,
            "summary": prediction.summary,
            "result_detail": {
                "risk_level": prediction.risk_level,
                "recommended_actions": prediction.recommended_actions,
                "metrics": prediction.metrics,
            },
            "explainability": {
                "top_factors": prediction.top_factors,
            },
            "model_version": "ruleset-v1",
        }
