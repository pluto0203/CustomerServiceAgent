"""
Application Settings
====================
Tất cả cấu hình đọc từ environment variables (hoặc .env file).
Dùng Pydantic Settings v2 để có type-safe config + validation tại startup.

Cách dùng ở bất kỳ module nào:
    from app.core.config import settings
    print(settings.DATABASE_URL)
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # Bỏ qua biến env không khai báo — an toàn hơn
    )

    # ------------------------------------------------------------------
    # App
    # ------------------------------------------------------------------
    APP_NAME: str = "customer-behavior-agent"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    SECRET_KEY: str = Field(
        ...,
        description="Bắt buộc. Đặt giá trị mạnh trong production.",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # ------------------------------------------------------------------
    # Database (PostgreSQL async via asyncpg)
    # ------------------------------------------------------------------
    DATABASE_URL: str = Field(
        ...,
        description="postgresql+asyncpg://user:pass@host:port/dbname",
    )

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync URL cho Alembic migrations (dùng psycopg thay asyncpg)."""
        return self.DATABASE_URL.replace(
            "postgresql+asyncpg://", "postgresql+psycopg://"
        )

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # ------------------------------------------------------------------
    # Redis / Celery
    # ------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ------------------------------------------------------------------
    # Vector DB (Qdrant)
    # ------------------------------------------------------------------
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION_CUSTOMERS: str = "customer_embeddings"

    # ------------------------------------------------------------------
    # LLM Providers
    # ------------------------------------------------------------------
    LLM_PROVIDER: Literal["local", "openai", "auto"] = "local"
    LLM_BASE_URL: str | None = "http://localhost:11434/v1"
    LLM_API_KEY: str | None = None
    LLM_MODEL: str | None = None
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-3-5-haiku-20241022"
    LLM_REQUEST_TIMEOUT: int = 300
    LLM_MAX_RETRIES: int = 1

    # ------------------------------------------------------------------
    # Web tools (optional enrichment)
    # ------------------------------------------------------------------
    WEB_TOOLS_ENABLED: bool = False
    WEB_SEARCH_ENABLED: bool = False
    WEB_FETCH_ENABLED: bool = False
    WEB_SEARCH_MAX_RESULTS: int = 3
    WEB_FETCH_MAX_CHARS: int = 3000
    WEB_TOOLS_TIMEOUT_SECONDS: float = 10.0
    WEB_TOOLS_USER_AGENT: str = "CustomerBehaviorAgent/1.0"
    WEB_ALLOWED_DOMAINS: str | None = None
    WEB_BLOCK_PRIVATE_NETWORK: bool = True

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None

    # ------------------------------------------------------------------
    # Agent system identity
    # ------------------------------------------------------------------
    AGENT_ID: str = "customer-behavior-agent"
    AGENT_VERSION: str = "1.0.0"


@lru_cache
def get_settings() -> Settings:
    """
    Trả về singleton Settings instance.
    Cache bằng lru_cache → chỉ đọc .env một lần duy nhất.

    Dùng làm FastAPI dependency:
        def endpoint(settings: Settings = Depends(get_settings)):
    """
    return Settings()  # type: ignore[call-arg]


# Module-level singleton cho các module không dùng DI (Celery workers, scripts...)
settings: Settings = get_settings()
