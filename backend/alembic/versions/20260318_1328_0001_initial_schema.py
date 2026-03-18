"""initial schema

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-03-18 13:28:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("full_name", sa.String(length=500), nullable=True),
        sa.Column("gender", sa.String(length=30), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("customer_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("total_orders", sa.Integer(), nullable=False),
        sa.Column("total_revenue", sa.Float(), nullable=False),
        sa.Column("avg_order_value", sa.Float(), nullable=True),
        sa.Column("last_order_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("days_since_last_order", sa.Integer(), nullable=True),
        sa.Column("engagement_score", sa.Float(), nullable=True),
        sa.Column("support_ticket_count", sa.Integer(), nullable=False),
        sa.Column("last_support_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("feedback_reviews", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feedback_tickets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feedback_social", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feedback_surveys", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("extra_attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ingestion_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_email"), "customers", ["email"], unique=False)
    op.create_index(op.f("ix_customers_ingestion_batch_id"), "customers", ["ingestion_batch_id"], unique=False)
    op.create_index(
        "ix_customers_email_unique",
        "customers",
        ["email"],
        unique=True,
        postgresql_where=text("email IS NOT NULL"),
    )
    op.create_index(
        "ix_customers_churn_features",
        "customers",
        ["days_since_last_order", "total_orders", "support_ticket_count"],
        unique=False,
    )

    op.create_table(
        "message_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_agent_id", sa.String(length=200), nullable=False),
        sa.Column("target_agent_id", sa.String(length=200), nullable=False),
        sa.Column("payload_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("celery_task_id", sa.String(length=200), nullable=True),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index(op.f("ix_message_logs_message_id"), "message_logs", ["message_id"], unique=False)
    op.create_index(op.f("ix_message_logs_correlation_id"), "message_logs", ["correlation_id"], unique=False)
    op.create_index(op.f("ix_message_logs_workflow_run_id"), "message_logs", ["workflow_run_id"], unique=False)
    op.create_index("ix_message_logs_correlation", "message_logs", ["correlation_id", "status"], unique=False)
    op.create_index("ix_message_logs_source_agent", "message_logs", ["source_agent_id", "created_at"], unique=False)

    op.create_table(
        "workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_agent_id", sa.String(length=200), nullable=True),
        sa.Column("workflow_name", sa.String(length=200), nullable=False),
        sa.Column("skills_requested", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("run_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input_record_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("records_succeeded", sa.Integer(), nullable=False),
        sa.Column("records_failed", sa.Integer(), nullable=False),
        sa.Column("model_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("prompt_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("agent_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflow_runs_message_id"), "workflow_runs", ["message_id"], unique=False)
    op.create_index(op.f("ix_workflow_runs_status"), "workflow_runs", ["status"], unique=False)
    op.create_index("ix_workflow_runs_status_created", "workflow_runs", ["status", "created_at"], unique=False)

    op.create_table(
        "run_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_name", sa.String(length=100), nullable=False),
        sa.Column("skill_version", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("result_detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explainability", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column("processing_ms", sa.Float(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_run_results_workflow_run_id"), "run_results", ["workflow_run_id"], unique=False)
    op.create_index(op.f("ix_run_results_customer_id"), "run_results", ["customer_id"], unique=False)
    op.create_index("ix_run_results_run_skill", "run_results", ["workflow_run_id", "skill_name"], unique=False)
    op.create_index("ix_run_results_customer_skill", "run_results", ["customer_id", "skill_name"], unique=False)
    op.create_index("ix_run_results_score_label", "run_results", ["skill_name", "score", "label"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_run_results_score_label", table_name="run_results")
    op.drop_index("ix_run_results_customer_skill", table_name="run_results")
    op.drop_index("ix_run_results_run_skill", table_name="run_results")
    op.drop_index(op.f("ix_run_results_customer_id"), table_name="run_results")
    op.drop_index(op.f("ix_run_results_workflow_run_id"), table_name="run_results")
    op.drop_table("run_results")

    op.drop_index("ix_workflow_runs_status_created", table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_status"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_message_id"), table_name="workflow_runs")
    op.drop_table("workflow_runs")

    op.drop_index("ix_message_logs_source_agent", table_name="message_logs")
    op.drop_index("ix_message_logs_correlation", table_name="message_logs")
    op.drop_index(op.f("ix_message_logs_workflow_run_id"), table_name="message_logs")
    op.drop_index(op.f("ix_message_logs_correlation_id"), table_name="message_logs")
    op.drop_index(op.f("ix_message_logs_message_id"), table_name="message_logs")
    op.drop_table("message_logs")

    op.drop_index("ix_customers_churn_features", table_name="customers")
    op.drop_index("ix_customers_email_unique", table_name="customers")
    op.drop_index(op.f("ix_customers_ingestion_batch_id"), table_name="customers")
    op.drop_index(op.f("ix_customers_email"), table_name="customers")
    op.drop_table("customers")
