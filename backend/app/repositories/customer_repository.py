from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.schemas.customer import CustomerBatch, CustomerRecord


class CustomerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        return await self.db.get(Customer, customer_id)

    async def get_many_by_ids(self, customer_ids: Sequence[UUID]) -> list[Customer]:
        if not customer_ids:
            return []
        stmt = select(Customer).where(Customer.id.in_(customer_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def upsert_batch(self, batch: CustomerBatch) -> list[Customer]:
        persisted: list[Customer] = []
        for record in batch.records:
            customer = await self._find_existing(record)
            if customer is None:
                customer = Customer(id=record.customer_id)
                self.db.add(customer)

            self._apply_record(customer, record, batch.batch_id)
            persisted.append(customer)

        await self.db.flush()
        return persisted

    async def _find_existing(self, record: CustomerRecord) -> Customer | None:
        customer = await self.db.get(Customer, record.customer_id)
        if customer is not None:
            return customer

        if record.email:
            stmt = select(Customer).where(Customer.email == str(record.email))
            result = await self.db.execute(stmt)
            customer = result.scalar_one_or_none()
            if customer is not None:
                return customer

        for system_name, external_id in record.external_ids.items():
            stmt = select(Customer).where(
                Customer.external_ids.contains({system_name: external_id})
            )
            result = await self.db.execute(stmt)
            customer = result.scalar_one_or_none()
            if customer is not None:
                return customer

        return None

    def _apply_record(self, customer: Customer, record: CustomerRecord, batch_id: UUID) -> None:
        customer.email = str(record.email) if record.email else None
        customer.phone = record.phone
        customer.full_name = record.full_name
        customer.gender = record.gender
        customer.address = record.extra_attributes.get("address")
        customer.customer_created_at = record.customer_created_at or record.created_at
        customer.external_ids = record.external_ids

        customer.total_orders = record.behavioral.total_orders
        customer.total_revenue = record.behavioral.total_revenue
        customer.avg_order_value = record.behavioral.avg_order_value
        customer.last_order_at = record.behavioral.last_order_at
        customer.days_since_last_order = record.behavioral.days_since_last_order
        customer.engagement_score = record.behavioral.engagement_score
        customer.support_ticket_count = record.behavioral.support_ticket_count
        customer.last_support_at = record.behavioral.last_support_at

        customer.feedback_reviews = record.feedback.reviews
        customer.feedback_tickets = record.feedback.support_tickets
        customer.feedback_social = record.feedback.social_comments
        customer.feedback_surveys = record.feedback.survey_responses

        customer.source = record.source.value
        customer.schema_version = record.schema_version
        customer.extra_attributes = record.extra_attributes
        customer.ingestion_batch_id = batch_id
