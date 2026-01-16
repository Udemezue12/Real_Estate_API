from datetime import datetime
import uuid
from typing import List, Optional

from fastapi import HTTPException
from models.models import RentalListing
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload


class RentalListingRepo:
    def __init__(self, db):
        self.db = db

    async def get_listing_id(self, item_id: uuid.UUID) -> RentalListing:
        stmt = (
            select(RentalListing)
            .options(
                selectinload(RentalListing.gallery),
                selectinload(RentalListing.state),
                selectinload(RentalListing.lga),
                selectinload(RentalListing.renter),
                selectinload(RentalListing.listed_by),
            )
            .where(RentalListing.id == item_id)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def create(self, data: dict) -> RentalListing:
        item = insert(RentalListing).values(**data).returning(RentalListing)
        result = await self.db.execute(item)
        try:
            await self.db.commit()
            await self.db.refresh(result)
            return result.scalar_one()
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create listing")

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[RentalListing]:
        result = await self.db.execute(
            select(RentalListing).where(RentalListing.listed_by_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_address(self, address: str) -> RentalListing | None:
        result = await self.db.execute(
            select(RentalListing).where(RentalListing.address == address)
        )
        return result.scalar_one_or_none()

    async def update(
        self, listing_id: uuid.UUID, data: dict
    ) -> Optional[RentalListing]:
        stmt = (
            update(RentalListing)
            .where(RentalListing.id == listing_id)
            .values(**data)
            .returning(RentalListing)
        )
        try:
            result = await self.db.execute(stmt)
            await self.db.commit()
            updated = result.scalar_one_or_none()
            if updated:
                await self.db.refresh(updated)
            return updated
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update listing")

    async def get_by_id(self, listing_id: uuid.UUID) -> Optional[RentalListing]:
        stmt = select(RentalListing).where(RentalListing.id == listing_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, page: int = 1, per_page: int = 20) -> List[RentalListing]:
        stmt = (
            select(RentalListing)
            .where(RentalListing.is_available == True)
            .options(
                selectinload(RentalListing.state),
                selectinload(RentalListing.lga),
                selectinload(RentalListing.renter),
                selectinload(RentalListing.gallery),
                selectinload(RentalListing.listed_by),
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_state(
        self, state_id: uuid.UUID, page: int = 1, per_page: int = 20
    ):
        stmt = (
            (
                select(RentalListing)
                .where(RentalListing.is_available == True)
                .options(
                    selectinload(RentalListing.state),
                    selectinload(RentalListing.lga),
                    selectinload(RentalListing.renter),
                    selectinload(RentalListing.gallery),
                    selectinload(RentalListing.listed_by),
                )
                .where(RentalListing.state_id == state_id)
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_lga(self, lga_id: uuid.UUID, page: int = 1, per_page: int = 20):
        stmt = (
            (
                select(RentalListing)
                .where(RentalListing.is_available == True)
                .options(
                    selectinload(RentalListing.state),
                    selectinload(RentalListing.lga),
                    selectinload(RentalListing.renter),
                    selectinload(RentalListing.gallery),
                    selectinload(RentalListing.listed_by),
                )
                .where(RentalListing.lga_id == lga_id)
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def mark_as_unavailable(self, listing_id: uuid.UUID, user_id: uuid.UUID):
        stmt = (
            update(RentalListing)
            .where(
                RentalListing.id == listing_id,
                RentalListing.listed_by_id == user_id,
                RentalListing.is_available == True,
            )
            .values(is_available=False, unavailable_at=datetime.utcnow())
            .returning(RentalListing)
        )

        try:
            result = await self.db.execute(stmt)
            await self.db.commit()
            rental = result.scalar_one_or_none()

            return rental
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(500, "Failed to mark listing as unavailable")

    async def mark_as_available(self, listing_id: uuid.UUID, user_id: uuid.UUID):
        stmt = (
            update(RentalListing)
            .where(
                RentalListing.id == listing_id,
                RentalListing.listed_by_id == user_id,
                RentalListing.is_available == False,
            )
            .values(is_available=False, unavailable_at=datetime.utcnow())
            .returning(RentalListing)
        )

        try:
            result = await self.db.execute(stmt)
            await self.db.commit()
            rental = result.scalar_one_or_none()

            return rental
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(500, "Failed to mark listing as unavailable")

    async def delete(self, listing_id: uuid.UUID, user_id: uuid.UUID):
        stmt = (
            update(RentalListing)
            .where(
                RentalListing.id == listing_id, RentalListing.listed_by_id == user_id
            )
            .values(is_available=False, unavailable_at=datetime.utcnow())
            .returning(RentalListing.id)
        )

        try:
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.scalar_one_or_none()
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(500, "Failed to delete rental")

    async def delete_all(self) -> RentalListing:
        stmt = delete(RentalListing)
        result = await self.db.execute(stmt)
        try:
            await self.db.commit()
            return result.rowcount
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to delete all listings")
