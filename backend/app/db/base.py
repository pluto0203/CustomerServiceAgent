"""
SQLAlchemy Declarative Base
===========================
Tất cả ORM models kế thừa từ Base class này.

TimestampMixin cung cấp created_at / updated_at tự động cho mọi bảng,
không cần khai báo lại ở từng model.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Root base class cho tất cả ORM models."""
    pass


class TimestampMixin:
    """
    Mixin thêm created_at và updated_at tự động.
    Kế thừa sau Base:
        class MyModel(TimestampMixin, Base): ...
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
