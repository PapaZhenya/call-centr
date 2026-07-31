from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    # The app works with aware-UTC datetimes everywhere; naive TIMESTAMP
    # columns make asyncpg reject those values, so every Mapped[datetime]
    # must be timestamptz (see migration 0004).
    type_annotation_map = {datetime: DateTime(timezone=True)}


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
