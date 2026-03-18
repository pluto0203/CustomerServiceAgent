from __future__ import annotations

from uuid import uuid4

from app.models.customer import Customer
from app.services.agent.processing_service import AgentProcessingService
from app.skills.churn_prediction import ChurnPredictionService
from app.skills.sentiment_analysis import SentimentAnalysisService


def build_customer(**overrides: object) -> Customer:
    payload = {
        "id": uuid4(),
        "email": "customer@example.com",
        "source": "agent_a2a",
        "external_ids": {},
        "schema_version": "1.0",
        "extra_attributes": {},
        "total_orders": 0,
        "total_revenue": 0.0,
        "support_ticket_count": 0,
        "feedback_reviews": [],
        "feedback_tickets": [],
        "feedback_social": [],
        "feedback_surveys": [],
    }
    payload.update(overrides)
    return Customer(**payload)


def test_churn_prediction_returns_high_risk_for_inactive_customer() -> None:
    service = ChurnPredictionService()
    customer = build_customer(
        total_orders=9,
        total_revenue=8_500_000,
        days_since_last_order=120,
        engagement_score=0.21,
        support_ticket_count=4,
    )

    result = service.analyze_many([customer])[0]

    assert result["skill_name"] == "churn_prediction"
    assert result["label"] in {"high", "critical"}
    assert result["score"] is not None and result["score"] >= 0.62
    assert result["result_detail"]["recommended_actions"]
    assert result["explainability"]["top_factors"]


def test_sentiment_analysis_detects_negative_feedback() -> None:
    service = SentimentAnalysisService()
    customer = build_customer(
        feedback_tickets=["Issue still unresolved after update.", "No follow up from support team."],
        feedback_surveys=["Needs better reliability"],
    )

    result = service.analyze_many([customer])[0]

    assert result["skill_name"] == "sentiment_analysis"
    assert result["label"] == "negative"
    assert result["score"] is not None and result["score"] < 0
    assert result["result_detail"]["topics"]


def test_processing_service_builds_multiskill_customer_result() -> None:
    service = AgentProcessingService()
    customer = build_customer(
        total_orders=3,
        total_revenue=2_600_000,
        days_since_last_order=30,
        engagement_score=0.79,
        support_ticket_count=1,
        feedback_reviews=["Product keeps improving."],
        feedback_social=["Useful features"],
    )

    skill_results = service._build_skill_results([customer])
    skill_map = {item["skill_name"]: item for item in skill_results}
    customer_result = service._build_customer_result(
        customer,
        skill_map["segment_insights"],
        skill_map["churn_prediction"],
        skill_map["sentiment_analysis"],
    )

    assert {item["skill_name"] for item in skill_results} == {
        "churn_prediction",
        "sentiment_analysis",
        "segment_insights",
    }
    assert customer_result["status"] == "analysis_ready"
    assert customer_result["churn_risk"] is not None
    assert customer_result["sentiment"] is not None
    assert customer_result["recommendations"]
