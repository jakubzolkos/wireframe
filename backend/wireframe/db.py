import logging
from typing import Annotated, AsyncIterator, Type
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine("postgresql://postgres:postgres@localhost:5432/wireframe", echo=True)
AsyncSessionLocal = async_sessionmaker(engine, autoflush=False)

async def get_session() -> AsyncIterator[async_sessionmaker]:
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except SQLAlchemyError as e:
        logging.error(f"Database error: {e}")
        raise e

AsyncSession = Annotated[async_sessionmaker, Depends(get_session)]


class Base(DeclarativeBase):
    pass


class CRUD:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, model: Type[Base], id: UUID) -> Base:
        result = await self.session.execute(
            select(model).where(model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, model: Type[Base], data: dict) -> Base:
        new_obj = model(**data)
        self.session.add(new_obj)
        await self.session.commit()
        return new_obj
    
    async def update(self, model: Type[Base], id: UUID, data: dict) -> Base:
        obj = await self.get(model, id)
        if not obj:
            raise HTTPException(status_code=404, detail="Object not found")
        for key, value in data.items():
            setattr(obj, key, value)

    async def delete(self, model: Type[Base], id: UUID) -> Base:
        obj = await self.get(model, id)
        if not obj:
            raise HTTPException(status_code=404, detail="Object not found")
        await self.session.delete(obj)
        await self.session.commit()
        return obj

    async def list(self, model: Type[Base]) -> list[Base]:
        result = await self.session.execute(
            select(model)
        )
        return result.scalars().all()

    async def filter(self, model: Type[Base], **kwargs) -> list[Base]:
        result = await self.session.execute(
            select(model).where(**kwargs)
        )
        return result.scalars().all()