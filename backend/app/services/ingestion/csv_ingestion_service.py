from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.db.session import async_session
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import BehavioralSnapshot, CustomerBatch, CustomerRecord, DataSource, TextFeedback


@dataclass(slots=True)
class CSVIngestionResult:
    filename: str
    total_rows: int
    ingested_rows: int
    failed_rows: int
    batch_id: str | None
    customer_ids: list[str]
    errors: list[dict[str, Any]]
    dry_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "total_rows": self.total_rows,
            "ingested_rows": self.ingested_rows,
            "failed_rows": self.failed_rows,
            "batch_id": self.batch_id,
            "customer_ids": self.customer_ids,
            "errors": self.errors,
            "dry_run": self.dry_run,
        }


class CSVIngestionService:
    REQUIRED_IDENTITY_COLUMNS = {"email", "phone", "customer_id"}

    def __init__(self) -> None:
        self._known_columns = {
            "customer_id",
            "email",
            "phone",
            "full_name",
            "gender",
            "address",
            "customer_created_at",
            "created_at",
            "total_orders",
            "total_revenue",
            "avg_order_value",
            "last_order_at",
            "days_since_last_order",
            "engagement_score",
            "support_ticket_count",
            "last_support_at",
            "feedback_reviews",
            "feedback_tickets",
            "feedback_social",
            "feedback_surveys",
            "external_ids_json",
            "external_hubspot_id",
            "external_zoho_id",
            "external_crm_id",
            "schema_version",
        }

    async def ingest_csv_bytes(
        self,
        *,
        content: bytes,
        filename: str,
        source_agent_id: str | None = None,
        dry_run: bool = False,
    ) -> CSVIngestionResult:
        rows = self._parse_csv_rows(content)
        if not rows:
            return CSVIngestionResult(
                filename=filename,
                total_rows=0,
                ingested_rows=0,
                failed_rows=0,
                batch_id=None,
                customer_ids=[],
                errors=[],
                dry_run=dry_run,
            )

        self._validate_identity_columns(rows[0].keys())

        valid_records: list[CustomerRecord] = []
        errors: list[dict[str, Any]] = []

        for idx, row in enumerate(rows, start=2):
            try:
                record = self._row_to_record(row)
                valid_records.append(record)
            except Exception as exc:
                errors.append({"row": idx, "error": str(exc)})

        if not valid_records:
            return CSVIngestionResult(
                filename=filename,
                total_rows=len(rows),
                ingested_rows=0,
                failed_rows=len(errors),
                batch_id=None,
                customer_ids=[],
                errors=errors,
                dry_run=dry_run,
            )

        batch = CustomerBatch(records=valid_records, source_agent_id=source_agent_id)

        if dry_run:
            return CSVIngestionResult(
                filename=filename,
                total_rows=len(rows),
                ingested_rows=len(valid_records),
                failed_rows=len(errors),
                batch_id=str(batch.batch_id),
                customer_ids=[str(record.customer_id) for record in valid_records],
                errors=errors,
                dry_run=True,
            )

        async with async_session() as db:
            repo = CustomerRepository(db)
            persisted = await repo.upsert_batch(batch)
            await db.commit()

        return CSVIngestionResult(
            filename=filename,
            total_rows=len(rows),
            ingested_rows=len(persisted),
            failed_rows=len(errors),
            batch_id=str(batch.batch_id),
            customer_ids=[str(item.id) for item in persisted],
            errors=errors,
            dry_run=False,
        )

    def _parse_csv_rows(self, content: bytes) -> list[dict[str, str]]:
        text = content.decode("utf-8-sig")
        stream = io.StringIO(text)
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            return []

        normalized_fieldnames = [self._normalize_key(name) for name in reader.fieldnames]
        reader.fieldnames = normalized_fieldnames

        rows: list[dict[str, str]] = []
        for raw_row in reader:
            row: dict[str, str] = {}
            for key, value in raw_row.items():
                if key is None:
                    continue
                row[self._normalize_key(key)] = (value or "").strip()
            if any(value for value in row.values()):
                rows.append(row)
        return rows

    def _validate_identity_columns(self, headers: Any) -> None:
        normalized_headers = {self._normalize_key(str(header)) for header in headers}
        if not normalized_headers.intersection(self.REQUIRED_IDENTITY_COLUMNS):
            allowed = ", ".join(sorted(self.REQUIRED_IDENTITY_COLUMNS))
            raise ValueError(f"CSV phải có ít nhất một cột định danh: {allowed}")

    def _row_to_record(self, row: dict[str, str]) -> CustomerRecord:
        customer_id = self._parse_uuid(row.get("customer_id"))
        total_orders = self._parse_int(row.get("total_orders"), default=0)
        total_revenue = self._parse_float(row.get("total_revenue"), default=0.0)
        avg_order_value = self._parse_float(row.get("avg_order_value"), default=None)
        last_order_at = self._parse_datetime(row.get("last_order_at"))
        days_since_last_order = self._parse_int(row.get("days_since_last_order"), default=None)

        if days_since_last_order is None and last_order_at is not None:
            now = datetime.now(timezone.utc)
            days_since_last_order = max((now - last_order_at).days, 0)

        behavioral = BehavioralSnapshot(
            total_orders=total_orders,
            total_revenue=total_revenue,
            avg_order_value=avg_order_value,
            last_order_at=last_order_at,
            days_since_last_order=days_since_last_order,
            engagement_score=self._parse_float(row.get("engagement_score"), default=None),
            support_ticket_count=self._parse_int(row.get("support_ticket_count"), default=0) or 0,
            last_support_at=self._parse_datetime(row.get("last_support_at")),
        )

        feedback = TextFeedback(
            reviews=self._parse_text_list(row.get("feedback_reviews")),
            support_tickets=self._parse_text_list(row.get("feedback_tickets")),
            social_comments=self._parse_text_list(row.get("feedback_social")),
            survey_responses=self._parse_text_list(row.get("feedback_surveys")),
        )

        external_ids = self._parse_external_ids(row)
        extra_attributes = {
            key: value
            for key, value in row.items()
            if key not in self._known_columns and value
        }

        payload: dict[str, Any] = {
            "external_ids": external_ids,
            "email": row.get("email") or None,
            "phone": row.get("phone") or None,
            "full_name": row.get("full_name") or None,
            "gender": row.get("gender") or None,
            "customer_created_at": self._parse_datetime(row.get("customer_created_at")),
            "created_at": self._parse_datetime(row.get("created_at")),
            "behavioral": behavioral,
            "feedback": feedback,
            "extra_attributes": {
                **extra_attributes,
                "address": row.get("address") or None,
            },
            "source": DataSource.CSV_UPLOAD,
            "schema_version": row.get("schema_version") or "1.0",
        }
        if customer_id is not None:
            payload["customer_id"] = customer_id
        return CustomerRecord(**payload)

    def _normalize_key(self, key: str) -> str:
        return key.strip().lower().replace(" ", "_")

    def _parse_int(self, value: str | None, *, default: int | None) -> int | None:
        if value is None or value == "":
            return default
        cleaned = value.replace(",", "").strip()
        return int(cleaned)

    def _parse_float(self, value: str | None, *, default: float | None) -> float | None:
        if value is None or value == "":
            return default
        cleaned = value.replace(",", "").strip()
        return float(cleaned)

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if value is None or value == "":
            return None

        normalized = value.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _parse_uuid(self, value: str | None) -> UUID | None:
        if value is None or value == "":
            return None
        return UUID(value.strip())

    def _parse_text_list(self, value: str | None) -> list[str]:
        if value is None:
            return []
        cleaned = value.strip()
        if not cleaned:
            return []

        for separator in ("|", ";", "\n"):
            if separator in cleaned:
                return [item.strip() for item in cleaned.split(separator) if item.strip()]

        return [cleaned]

    def _parse_external_ids(self, row: dict[str, str]) -> dict[str, str]:
        external_ids: dict[str, str] = {}
        raw_json = row.get("external_ids_json")
        if raw_json:
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict):
                external_ids.update({str(k): str(v) for k, v in parsed.items()})

        if row.get("external_hubspot_id"):
            external_ids["hubspot"] = row["external_hubspot_id"]
        if row.get("external_zoho_id"):
            external_ids["zoho"] = row["external_zoho_id"]
        if row.get("external_crm_id"):
            external_ids["crm"] = row["external_crm_id"]

        return external_ids
