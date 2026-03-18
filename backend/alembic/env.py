"""
Alembic Environment
===================
Chạy migrations theo 2 mode:
- offline: generate SQL script mà không cần DB connection (dùng cho review).
- online:  kết nối DB thật, chạy migration trực tiếp.

Dùng sync engine (psycopg) vì Alembic chưa support asyncpg đầy đủ.
DATABASE_URL_SYNC được computed từ DATABASE_URL trong config.
"""

from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Import tất cả models để Alembic autogenerate phát hiện thay đổi schema
# ---------------------------------------------------------------------------
from app.core.config import settings
from app.db.base import Base
import app.models.customer       # noqa: F401
import app.models.workflow_run   # noqa: F401
import app.models.message_log    # noqa: F401
import app.models.run_result     # noqa: F401

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

# Override sqlalchemy.url từ app settings (không hardcode trong alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Chạy migrations ở offline mode.
    Sinh ra SQL script, không cần kết nối DB thật.
    Dùng: alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Chạy migrations ở online mode — kết nối DB thật.
    Dùng: alembic upgrade head
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,    # Không pool trong migration job
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,              # Detect column type changes
            compare_server_default=True,    # Detect server_default changes
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
