# backend/alembic/env.py
from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

# Make sure the backend directory is importable so we can "from app.models import Base"
# env.py lives at backend/alembic/env.py -> backend dir is one level up
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Alembic Config object
config = context.config

# If DATABASE_URL env var is set (common on hosting platforms), prefer it.
# Convert async URL (postgresql+asyncpg://...) -> sync driver for Alembic (postgresql+psycopg2://...)
def _normalize_for_alembic(url: str | None) -> str | None:
    if not url:
        return url
    # replace +asyncpg with +psycopg2 (so alembic uses a sync driver)
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "+psycopg2")
    return url

env_db_url = os.getenv("DATABASE_URL")
if env_db_url:
    config.set_main_option("sqlalchemy.url", _normalize_for_alembic(env_db_url))
else:
    # If alembic.ini contains an async url, normalize that too
    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url and "+asyncpg" in ini_url:
        config.set_main_option("sqlalchemy.url", _normalize_for_alembic(ini_url))

# Interpret the config file for Python logging.
if config.config_file_name:
    fileConfig(config.config_file_name)

# Import your models' metadata (for autogenerate support)
# Now that BACKEND_DIR is in sys.path, this should import cleanly.
from app.models import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode (SQL script generation)."""
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(
            "No sqlalchemy.url configured for Alembic. Set DATABASE_URL or edit alembic.ini."
        )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode (connect to DB and run)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
