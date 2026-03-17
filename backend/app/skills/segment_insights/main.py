from __future__ import annotations

import json
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.customer import Customer


@dataclass(slots=True)
class SegmentInsight:
    customer_id: UUID
    segment_code: str
    segment_name: str
    score: float
    confidence: float
    summary: str
    recommended_actions: list[str]
    top_signals: list[str]
    metrics: dict[str, Any]


class SegmentInsightsService:
    """
    Skill runtime theo pattern:
    - instruction.md: system instruction cho LLM
    - schema.json: output contract
    - main.py: business logic + data access + LLM call wrapper
    """

    skill_name = "segment_insights"
    skill_version = "1.1"

    def __init__(
        self,
        instruction_path: Path | None = None,
        schema_path: Path | None = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent
        self.instruction_path = instruction_path or (base_dir / "instruction.md")
        self.schema_path = schema_path or (base_dir / "schema.json")
        self._instruction_text = self._load_instruction()
        self._response_schema = self._load_schema()

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
            insight = self._from_ai_or_rules(customer, ai_result)
            results.append(self._to_run_result(insight))
        return results

    def _load_instruction(self) -> str:
        return self.instruction_path.read_text(encoding="utf-8")

    def _load_schema(self) -> dict[str, Any]:
        return json.loads(self.schema_path.read_text(encoding="utf-8"))

    def _call_ai(self, customer: Customer) -> dict[str, Any] | None:
        """
        Optional AI call. Nếu không có API key hoặc SDK, fallback về rule-based.
        """
        if not settings.OPENAI_API_KEY:
            return None

        try:
            openai_module = importlib.import_module("openai")
            openai_client_cls = getattr(openai_module, "OpenAI")
            client = openai_client_cls(api_key=settings.OPENAI_API_KEY)
            prompt_payload = self._build_customer_payload(customer)

            response = client.responses.create(
                model=settings.OPENAI_MODEL,
                input=[
                    {"role": "system", "content": self._instruction_text},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "customer": prompt_payload,
                                "required_schema": self._response_schema,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                temperature=0.2,
            )

            text_output = getattr(response, "output_text", None)
            if not text_output:
                return None
            return json.loads(text_output)
        except Exception:
            return None

    def _from_ai_or_rules(self, customer: Customer, ai_result: dict[str, Any] | None) -> SegmentInsight:
        if ai_result is not None and self._looks_like_valid_result(ai_result):
            return SegmentInsight(
                customer_id=customer.id,
                segment_code=str(ai_result["segment_code"]),
                segment_name=str(ai_result["segment_name"]),
                score=float(ai_result["score"]),
                confidence=float(ai_result["confidence"]),
                summary=str(ai_result["summary"]),
                recommended_actions=[str(item) for item in ai_result.get("recommended_actions", [])],
                top_signals=[str(item) for item in ai_result.get("top_signals", [])],
                metrics=dict(ai_result.get("metrics", {})),
            )

        return self._rule_based_insight(customer)

    def _build_customer_payload(self, customer: Customer) -> dict[str, Any]:
        return {
            "customer_id": str(customer.id),
            "total_orders": customer.total_orders or 0,
            "total_revenue": customer.total_revenue or 0.0,
            "days_since_last_order": customer.days_since_last_order,
            "engagement_score": customer.engagement_score or 0.0,
            "support_ticket_count": customer.support_ticket_count or 0,
            "feedback_reviews_count": len(customer.feedback_reviews or []),
            "feedback_tickets_count": len(customer.feedback_tickets or []),
            "feedback_social_count": len(customer.feedback_social or []),
            "feedback_surveys_count": len(customer.feedback_surveys or []),
        }

    def _looks_like_valid_result(self, result: dict[str, Any]) -> bool:
        required = {
            "segment_code",
            "segment_name",
            "score",
            "confidence",
            "summary",
            "recommended_actions",
            "top_signals",
            "metrics",
        }
        return required.issubset(result.keys())

    def _rule_based_insight(self, customer: Customer) -> SegmentInsight:
        total_revenue = customer.total_revenue or 0.0
        total_orders = customer.total_orders or 0
        days_since_last_order = customer.days_since_last_order
        engagement_score = customer.engagement_score or 0.0
        support_ticket_count = customer.support_ticket_count or 0
        review_count = len(customer.feedback_reviews or [])
        ticket_text_count = len(customer.feedback_tickets or [])
        social_count = len(customer.feedback_social or [])
        survey_count = len(customer.feedback_surveys or [])
        feedback_volume = review_count + ticket_text_count + social_count + survey_count

        signals: list[str] = []
        actions: list[str] = []
        segment_code = "new_low_signal"
        segment_name = "New / Low Signal"
        score = 0.35
        confidence = 0.55

        if total_revenue >= 10_000_000 and (days_since_last_order is None or days_since_last_order <= 30):
            segment_code = "loyal_vip"
            segment_name = "Loyal VIP"
            score = 0.92
            confidence = 0.9
            signals.extend([
                "Gia tri doanh thu cao",
                "Mua gan day",
            ])
            if engagement_score >= 0.6:
                signals.append("Tuong tac tot")
            actions.extend([
                "Uu tien chuong trinh loyalty hoac VIP tier",
                "Upsell san pham premium hoac cross-sell goi bo sung",
            ])
        elif total_revenue >= 5_000_000 and days_since_last_order is not None and days_since_last_order > 60:
            segment_code = "at_risk_vip"
            segment_name = "At-Risk VIP"
            score = 0.88
            confidence = 0.86
            signals.extend([
                "Gia tri doanh thu cao",
                "Da lau khong quay lai mua",
            ])
            if support_ticket_count >= 2:
                signals.append("Co nhieu tuong tac ho tro")
            actions.extend([
                "Kich hoat win-back campaign ca nhan hoa",
                "CSKH chu dong lien he voi uu dai giu chan",
            ])
        elif support_ticket_count >= 3 and total_revenue >= 1_000_000:
            segment_code = "support_heavy"
            segment_name = "Support-Heavy Value Customer"
            score = 0.77
            confidence = 0.8
            signals.extend([
                "Co gia tri mua hang",
                "Tan suat ticket ho tro cao",
            ])
            actions.extend([
                "Phan tich nguyen nhan ticket lap lai",
                "Uu tien care flow sau mua va quality assurance",
            ])
        elif engagement_score >= 0.65 and (days_since_last_order is None or days_since_last_order <= 45):
            segment_code = "active_growth"
            segment_name = "Active Growth"
            score = 0.74
            confidence = 0.78
            signals.extend([
                "Tuong tac tot",
                "Hoat dong gan day",
            ])
            if total_orders >= 2:
                signals.append("Da co hanh vi mua lap lai")
            actions.extend([
                "Day campaign nurturing va recommendation",
                "Thu nghiem bundle offer de tang AOV",
            ])
        elif days_since_last_order is not None and days_since_last_order > 90:
            segment_code = "dormant"
            segment_name = "Dormant"
            score = 0.69
            confidence = 0.76
            signals.extend([
                "Khong co giao dich gan day",
                "Muc do ngu dong cao",
            ])
            actions.extend([
                "Chay chuong trinh reactivation theo nguyen nhan roi bo",
                "Gioi han tan suat spam, uu tien thong diep win-back ro rang",
            ])
        elif total_orders <= 1 and feedback_volume <= 1:
            segment_code = "new_low_signal"
            segment_name = "New / Low Signal"
            score = 0.38
            confidence = 0.6
            signals.extend([
                "Du lieu han che",
                "Chua du hanh vi de ket luan sau",
            ])
            actions.extend([
                "Tiep tuc thu thap them hanh vi tuong tac",
                "Onboarding flow co giao duc san pham va first-value activation",
            ])
        else:
            segment_code = "standard_repeat"
            segment_name = "Standard Repeat Customer"
            score = 0.58
            confidence = 0.7
            signals.extend([
                "Co mua hang lap lai o muc co ban",
                "Chua thuoc nhom VIP hoac At-Risk ro rang",
            ])
            actions.extend([
                "Nuoi duong bang automation theo vong doi mua hang",
                "Kiem tra co hoi nang cap sang nhom loyalty",
            ])

        if feedback_volume > 0:
            signals.append(f"Co {feedback_volume} dau hieu feedback text")

        summary = self._build_summary(segment_name, total_orders, total_revenue, days_since_last_order)

        return SegmentInsight(
            customer_id=customer.id,
            segment_code=segment_code,
            segment_name=segment_name,
            score=score,
            confidence=confidence,
            summary=summary,
            recommended_actions=actions,
            top_signals=signals,
            metrics={
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "days_since_last_order": days_since_last_order,
                "engagement_score": engagement_score,
                "support_ticket_count": support_ticket_count,
                "feedback_volume": feedback_volume,
            },
        )

    def _to_run_result(self, insight: SegmentInsight) -> dict[str, Any]:
        return {
            "customer_id": insight.customer_id,
            "skill_name": self.skill_name,
            "skill_version": self.skill_version,
            "score": insight.score,
            "label": insight.segment_code,
            "confidence": insight.confidence,
            "summary": insight.summary,
            "result_detail": {
                "segment_code": insight.segment_code,
                "segment_name": insight.segment_name,
                "recommended_actions": insight.recommended_actions,
                "metrics": insight.metrics,
            },
            "explainability": {
                "top_signals": insight.top_signals,
            },
            "model_version": "ruleset-v1",
        }

    def _build_summary(
        self,
        segment_name: str,
        total_orders: int,
        total_revenue: float,
        days_since_last_order: int | None,
    ) -> str:
        recency_text = (
            f"{days_since_last_order} ngay tu lan mua cuoi"
            if days_since_last_order is not None
            else "chua co thong tin recency"
        )
        return (
            f"Khach hang duoc xep vao nhom {segment_name}. "
            f"Tong {total_orders} don, doanh thu {total_revenue:.0f}, {recency_text}."
        )
