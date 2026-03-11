"""
Alembic environment for Ussop.

Reads DATABASE_URL from the application settings so the same .env file
drives both the app and migrations.  Works with SQLite (dev) and
PostgreSQL (production) without any changes.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Make the project importable ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
USSOP_PKG    = PROJECT_ROOT / "ussop"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(USSOP_PKG))

# ── Load app settings & models ───────────────────────────────────────────────
from config.settings import settings          # noqa: E402
from models.database import Base              # noqa: E402
import models.auth                            # noqa: E402  (registers User/Role tables)

target_metadata = Base.metadata

# ── Alembic config ────────────────────────────────────────────────────────────
alembic_cfg = context.config

if alembic_cfg.config_file_name is not None:
    fileConfig(alembic_cfg.config_file_name)

# Override sqlalchemy.url from app settings so we don't duplicate it
alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


# ── Migration runners ─────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Generate SQL without a live DB connection (useful for review / CI)."""
    url = alembic_cfg.get_main_option("sqlalchemy.url")
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
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        alembic_cfg.get_section(alembic_cfg.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
