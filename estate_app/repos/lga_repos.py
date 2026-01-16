import uuid
from typing import List, Optional

from core.geoapify import geocode_address
from fastapi import HTTPException
from geoalchemy2.shape import from_shape
from models.models import LocalGovernmentArea, State
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload


class LGARepo:
    def __init__(self, db):
        self.db = db

    async def get_lga_state(self, state_name: str):
        result = await self.db.execute(
            select(State).where(State.name.ilike(state_name))
        )
        state = result.scalar_one_or_none()
        if not state:
            raise HTTPException(
                status_code=404, detail=f"State '{state_name}' not found"
            )

    async def create(self, name: str, state_id: uuid.UUID):
        point = await geocode_address(name)
        geom = from_shape(point, srid=4326)
        existing = await self.db.execute(
            select(LocalGovernmentArea).where(
                LocalGovernmentArea.name == name,
                LocalGovernmentArea.state_id == state_id,
            )
        )

        existing_lga = existing.scalars().first()
        if existing_lga:
            raise HTTPException(
                status_code=400, detail="The Local Government has already been created"
            )
        lga = LocalGovernmentArea(name=name, location=geom, state_id=state_id)
        self.db.add(lga)
        try:
            await self.db.commit()
            await self.db.refresh(lga, attribute_names=["state"])
            return lga
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create state")

    async def get_lga_name(self, name: str):
        existing_result = await self.db.execute(
            select(LocalGovernmentArea).where(LocalGovernmentArea.name.ilike(name))
        )
        existing_lga = existing_result.scalar_one_or_none()
        if existing_lga:
            raise HTTPException(status_code=400, detail=f"LGA '{name}' already exists")
        return existing_result

    async def get_one(self, name: str) -> Optional[LocalGovernmentArea]:
        result = await self.db.execute(
            select(LocalGovernmentArea)
            .where(LocalGovernmentArea.name == name)
            .options(selectinload(LocalGovernmentArea.state))
        )
        return result.scalar_one_or_none()

    async def get_one_by_id(self, lga_id: uuid.UUID) -> Optional[LocalGovernmentArea]:
        result = await self.db.execute(
            select(LocalGovernmentArea)
            .where(LocalGovernmentArea.id == lga_id)
            .options(selectinload(LocalGovernmentArea.state))
        )
        return result.scalar_one_or_none()

    async def validate_state_lga_match(
        self, state_id: uuid.UUID, lga_id: uuid.UUID
    ) -> LocalGovernmentArea:
        lga = await self.get_one_by_id(lga_id=lga_id)
        if not lga:
            raise HTTPException(status_code=404, detail="Not Found")

        if lga.state_id != state_id:
            raise HTTPException(
                status_code=400,
                detail=f"LGA '{lga.name}' does not belong to State with id {state_id}",
            )

        return lga

    async def get_all(self) -> List[LocalGovernmentArea]:
        result = await self.db.execute(select(LocalGovernmentArea))
        return result.scalars().all()

    async def get_all_with_state(self) -> List[LocalGovernmentArea]:
        result = await self.db.execute(
            select(LocalGovernmentArea).options(selectinload(LocalGovernmentArea.state))
        )
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Optional[LocalGovernmentArea]:
        result = await self.db.execute(
            select(LocalGovernmentArea).where(LocalGovernmentArea.name == name)
        )
        return result.scalar_one_or_none()

    async def update_one(
        self,
        lga_id: uuid.UUID,
        new_name: str | None = None,
        state_name: str | None = None,
    ):
        state_id = None
        if state_name:
            state = await self.get_lga_state(state_name=state_name)
        state_id = state.id
        stmt = update(LocalGovernmentArea).where(LocalGovernmentArea.id == lga_id)
        values = {}
        if new_name:
            values["name"] = new_name
        if state_id:
            values["state_id"] = state_id
        if not values:
            return await self.get_one_by_id(lga_id)
        stmt = stmt.values(**values).returning(LocalGovernmentArea)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def delete_one(self, name: str) -> LocalGovernmentArea:
        lga = await self.get_one(name)
        if not lga:
            raise HTTPException(status_code=404, detail="Not Found")

        await self.db.delete(lga)
        try:
            await self.db.commit()
            return lga
        except SQLAlchemyError:
            await self.db.rollback()
            raise
