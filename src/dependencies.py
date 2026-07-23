from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from src.services.target_api import TargetAPI
from src.db.database import AsyncSessionFactory


def get_target_api(request: Request) -> TargetAPI:
    return request.app.state.target_api


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session
