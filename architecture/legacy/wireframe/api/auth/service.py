import datetime
from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy import UUID, DateTime, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from wireframe.db import AsyncSession, get_session


class User(DeclarativeBase):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    
class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: str) -> User:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        r = result.scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="User not found")
        
        return r


async def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    yield AuthService(session)