# backend/app/db.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.engine.url import make_url

# Read raw env var (may be sync or async)
RAW_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://utsavam:utsavam_pass@localhost:5433/utsavam_dev",
)

def ensure_async_driver(url: str) -> str:
    """
    Ensure the URL uses an async DBAPI for SQLAlchemy asyncio (e.g. +asyncpg).
    If the URL is already async (contains '+'), return as-is.
    If it's a sync 'postgresql://' URL, convert to 'postgresql+asyncpg://'.
    """
    parsed = make_url(url)
    # If the dialect+driver already contains a driver (e.g. postgresql+asyncpg) keep it
    if parsed.drivername and "+" in parsed.drivername:
        return url
    # If it's a plain postgresql URL, convert to asyncpg
    if parsed.get_backend_name() == "postgresql":
        # build a new URL with +asyncpg
        async_driver = f"{parsed.get_backend_name()}+asyncpg"
        # make_url lets us replace drivername by creating a new URL string
        new_url = url.replace(parsed.drivername, async_driver, 1)
        return new_url
    # Otherwise, return unchanged
    return url

DATABASE_URL = ensure_async_driver(RAW_DATABASE_URL)

# Optional tuning (env vars are strings). If not present, defaults used.
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 20))

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
