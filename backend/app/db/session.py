"""
Database Session Factory
========================
Cung cấp async SQLAlchemy engine và session factory.

Cách dùng trong FastAPI endpoint (qua dependency injection):
    async def endpoint(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Customer))

Cách dùng trong Celery worker (context manager trực tiếp):
    async with async_session() as db:
        ...
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ---------------------------------------------------------------------------
# Engine — dùng asyncpg driver cho PostgreSQL async
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,     # Kiểm tra connection health trước khi dùng
    echo=settings.DEBUG,    # Log SQL queries khi DEBUG=True
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency — inject AsyncSession vào endpoint
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency cấp AsyncSession cho mỗi request.
    Tự động rollback nếu có exception, tự đóng session sau request.

    Dùng:
        async def endpoint(db: AsyncSession = Depends(get_db)):
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
