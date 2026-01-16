
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.declarative import declarative_base

from .settings import settings

DATABASE_URL = settings.DATABASE_URL
RENDER_DATABASE_URL = settings.RENDER_DATABASE_URL
async_engine: AsyncEngine = create_async_engine(
    RENDER_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_async():
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        raise
    finally:
        await session.close()


Base = declarative_base()
