from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, StaticPool

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}
if settings.sqlalchemy_database_url.startswith("sqlite") and ":memory:" in settings.sqlalchemy_database_url:
    engine_kwargs = {"poolclass": StaticPool}
elif settings.sqlalchemy_database_url.startswith("sqlite"):
    engine_kwargs = {"poolclass": NullPool}
else:
    engine_kwargs.update({"pool_size": 5, "max_overflow": 10, "connect_args": {"connect_timeout": 5}})

engine = create_async_engine(settings.sqlalchemy_database_url, **engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
