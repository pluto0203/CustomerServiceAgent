from __future__ import annotations

import importlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.customer import Customer


POSITIVE_PHRASES = {
    "great": 1.0,
    "love": 1.1,
    "good": 0.7,
    "useful": 0.7,
    "improving": 0.8,
    "quality": 0.5,
    "tot": 0.7,
    "hai long": 1.0,
    "on": 0.2,
}

NEGATIVE_PHRASES = {
    "issue": 0.8,
    "unresolved": 1.1,
    "error": 0.9,
    "errors": 0.9,
    "delay": 0.8,
    "slow": 0.7,
    "problem": 0.8,
    "bad": 0.9,
    "poor": 0.8,
    "cham": 0.8,
    "khong": 0.4,
    "loi": 0.9,
    "recurring": 0.8,
    "reliability": 0.7,
    "follow up": 0.7,
    "still": 0.3,
}

TOPIC_KEYWORDS = {
    "delivery": {"delivery", "ship", "shipping", "giao hang", "late", "delay", "cham"},
    "product_quality": {"quality", "device", "product", "san pham", "feature", "features"},
    "support_experience": {"support", "ticket", "issue", "follow up", "ho tro"},
    "reliability": {"error", "errors", "recurring", "unresolved", "reliability", "bug", "loi"},
    "usability": {"useful", "easy", "hard", "ui", "ux"},
}


@dataclass(slots=True)
class SentimentAnalysis:
    customer_id: UUID
    sentiment_label: str
    score: float
    confidence: float
    summary: str
    recommended_actions: list[str]
    top_signals: list[str]
    topics: list[str]
    metrics: dict[str, Any]


class SentimentAnalysisService:
    skill_name = "sentiment_analysis"
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
            sentiment = self._from_ai_or_rules(customer, ai_result)
            results.append(self._to_run_result(sentiment))
        return results

    def _call_ai(self, customer: Customer) -> dict[str, Any] | None:
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
                temperature=0.1,
            )

            text_output = getattr(response, "output_text", None)
            if not text_output:
                return None
            return json.loads(text_output)
        except Exception:
            return None

    def _from_ai_or_rules(
        self,
        customer: Customer,
        ai_result: dict[str, Any] | None,
    ) -> SentimentAnalysis:
        if ai_result is not None and self._looks_like_valid_result(ai_result):
            return SentimentAnalysis(
                customer_id=customer.id,
                sentiment_label=str(ai_result["sentiment_label"]),
                score=float(ai_result["score"]),
                confidence=float(ai_result["confidence"]),
                summary=str(ai_result["summary"]),
                recommended_actions=[str(item) for item in ai_result.get("recommended_actions", [])],
                top_signals=[str(item) for item in ai_result.get("top_signals", [])],
                topics=[str(item) for item in ai_result.get("topics", [])],
                metrics=dict(ai_result.get("metrics", {})),
            )

        return self._rule_based_analysis(customer)

    def _build_customer_payload(self, customer: Customer) -> dict[str, Any]:
        return {
            "customer_id": str(customer.id),
            "reviews": list(customer.feedback_reviews or []),
            "support_tickets": list(customer.feedback_tickets or []),
            "social_comments": list(customer.feedback_social or []),
            "survey_responses": list(customer.feedback_surveys or []),
        }

    def _looks_like_valid_result(self, result: dict[str, Any]) -> bool:
        required = {
            "sentiment_label",
            "score",
            "confidence",
            "summary",
            "recommended_actions",
            "top_signals",
            "topics",
            "metrics",
        }
        return required.issubset(result.keys())

    def _rule_based_analysis(self, customer: Customer) -> SentimentAnalysis:
        feedback_items = self._collect_feedback(customer)
        if not feedback_items:
            return SentimentAnalysis(
                customer_id=customer.id,
                sentiment_label="neutral",
                score=0.0,
                confidence=0.3,
                summary="Khong co du lieu feedback text de ket luan sentiment ro rang.",
                recommended_actions=[
                    "Thu thap them review, survey hoac ticket text truoc khi dien giai sentiment",
                ],
                top_signals=["Khong co feedback text"],
                topics=[],
                metrics={"feedback_count": 0, "positive_hits": 0, "negative_hits": 0},
            )

        total_raw_score = 0.0
        positive_hits = 0
        negative_hits = 0
        signal_counter: dict[str, int] = {}
        topic_counter: dict[str, int] = {}

        for source_name, text in feedback_items:
            normalized = self._normalize_text(text)
            signal_key = f"{source_name}: {text[:80]}"
            for phrase, weight in POSITIVE_PHRASES.items():
                if phrase in normalized:
                    total_raw_score += weight
                    positive_hits += 1
                    signal_counter[signal_key] = signal_counter.get(signal_key, 0) + 1
            for phrase, weight in NEGATIVE_PHRASES.items():
                if phrase in normalized:
                    total_raw_score -= weight
                    negative_hits += 1
                    signal_counter[signal_key] = signal_counter.get(signal_key, 0) + 1
            for topic_name, keywords in TOPIC_KEYWORDS.items():
                if any(keyword in normalized for keyword in keywords):
                    topic_counter[topic_name] = topic_counter.get(topic_name, 0) + 1

        normalized_score = math.tanh(total_raw_score / max(len(feedback_items), 1))
        normalized_score = round(max(-1.0, min(normalized_score, 1.0)), 4)
        sentiment_label = self._label_from_score(normalized_score, positive_hits, negative_hits)
        confidence = self._build_confidence(len(feedback_items), positive_hits, negative_hits, normalized_score)
        topics = [name for name, _ in sorted(topic_counter.items(), key=lambda item: item[1], reverse=True)[:3]]
        top_signals = [name for name, _ in sorted(signal_counter.items(), key=lambda item: item[1], reverse=True)[:4]]
        summary = self._build_summary(sentiment_label, normalized_score, len(feedback_items), topics)
        recommended_actions = self._recommended_actions(sentiment_label, topics)

        return SentimentAnalysis(
            customer_id=customer.id,
            sentiment_label=sentiment_label,
            score=normalized_score,
            confidence=confidence,
            summary=summary,
            recommended_actions=recommended_actions,
            top_signals=top_signals or [f"Phan tich {len(feedback_items)} feedback items"],
            topics=topics,
            metrics={
                "feedback_count": len(feedback_items),
                "positive_hits": positive_hits,
                "negative_hits": negative_hits,
                "source_breakdown": self._source_breakdown(feedback_items),
            },
        )

    def _collect_feedback(self, customer: Customer) -> list[tuple[str, str]]:
        feedback_items: list[tuple[str, str]] = []
        sources = {
            "review": customer.feedback_reviews or [],
            "ticket": customer.feedback_tickets or [],
            "social": customer.feedback_social or [],
            "survey": customer.feedback_surveys or [],
        }
        for source_name, texts in sources.items():
            for text in texts:
                if isinstance(text, str) and text.strip():
                    feedback_items.append((source_name, text.strip()))
        return feedback_items

    def _normalize_text(self, text: str) -> str:
        lowered = text.lower()
        lowered = lowered.replace("đ", "d")
        lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    def _label_from_score(self, score: float, positive_hits: int, negative_hits: int) -> str:
        if score <= -0.3:
            return "negative"
        if score >= 0.3:
            return "positive"
        if positive_hits > 0 and negative_hits > 0:
            return "mixed"
        return "neutral"

    def _build_confidence(
        self,
        feedback_count: int,
        positive_hits: int,
        negative_hits: int,
        score: float,
    ) -> float:
        confidence = 0.35 + min(feedback_count, 4) * 0.1
        if positive_hits or negative_hits:
            confidence += 0.1
        confidence += min(abs(score), 0.4)
        return round(min(confidence, 0.95), 4)

    def _build_summary(
        self,
        sentiment_label: str,
        score: float,
        feedback_count: int,
        topics: list[str],
    ) -> str:
        topic_text = ", ".join(topics) if topics else "khong co topic noi bat"
        return (
            f"Sentiment tong the la {sentiment_label} (score {score:.2f}) tren {feedback_count} feedback items; "
            f"topic noi bat: {topic_text}."
        )

    def _recommended_actions(self, sentiment_label: str, topics: list[str]) -> list[str]:
        topic_hint = f"uu tien xu ly topic {topics[0]}" if topics else "uu tien thu thap them goc nhin khach hang"
        if sentiment_label == "negative":
            return [
                f"CSKH follow-up chu dong va {topic_hint}",
                "Dong vong phan hoi voi khach bang hanh dong cu the, khong chi xin loi chung chung",
            ]
        if sentiment_label == "mixed":
            return [
                f"Giu diem manh nhung tach rieng friction de {topic_hint}",
                "Theo doi sentiment sau lan can thiệp tiep theo de xem xu huong co cai thien khong",
            ]
        if sentiment_label == "positive":
            return [
                "Khai thac review tich cuc cho referral, testimonial hoac upsell nhe",
                "Duy tri trai nghiem tot va moi khach de lai them feedback chat luong",
            ]
        return [
            "Thu thap them feedback dinh tinh truoc khi thay doi playbook cham soc",
            "Theo doi them topic lap lai trong review, ticket va survey",
        ]

    def _source_breakdown(self, feedback_items: list[tuple[str, str]]) -> dict[str, int]:
        breakdown: dict[str, int] = {}
        for source_name, _ in feedback_items:
            breakdown[source_name] = breakdown.get(source_name, 0) + 1
        return breakdown

    def _to_run_result(self, sentiment: SentimentAnalysis) -> dict[str, Any]:
        return {
            "customer_id": sentiment.customer_id,
            "skill_name": self.skill_name,
            "skill_version": self.skill_version,
            "score": sentiment.score,
            "label": sentiment.sentiment_label,
            "confidence": sentiment.confidence,
            "summary": sentiment.summary,
            "result_detail": {
                "sentiment_label": sentiment.sentiment_label,
                "recommended_actions": sentiment.recommended_actions,
                "topics": sentiment.topics,
                "metrics": sentiment.metrics,
            },
            "explainability": {
                "top_signals": sentiment.top_signals,
            },
            "model_version": "ruleset-v1",
        }
