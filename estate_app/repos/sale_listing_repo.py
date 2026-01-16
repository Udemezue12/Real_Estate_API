import uuid
from typing import List, Optional

from fastapi import HTTPException
from models.models import SaleListing
from models.enums import SOLD_BY
from sqlalchemy import delete, select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError


class SaleListingRepo:
    def __init__(self, db):
        self.db = db

    async def mark_as_sold(
        self, listing_id: uuid.UUID, user_id: uuid.UUID, sold_by: SOLD_BY
    ):
        stmt = (
            update(SaleListing)
            .where(
                SaleListing.id == listing_id,
                SaleListing.listed_by_id == user_id,
                SaleListing.is_available == True,
            )
            .values(is_available=False, sold_by=sold_by)
            .returning(SaleListing)
        )

        try:
            result = await self.db.execute(stmt)
            await self.db.commit()
            sold = result.scalar_one_or_none()
            return sold
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(500, "Failed to mark listing as sold")

    async def get_listing_id(self, item_id: uuid.UUID) -> SaleListing:
        stmt = (
            select(SaleListing)
            .options(
                selectinload(SaleListing.gallery),
                selectinload(SaleListing.state),
                selectinload(SaleListing.lga),
                selectinload(SaleListing.seller),
                selectinload(SaleListing.listed_by),
            )
            .where(SaleListing.id == item_id)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def create(self, data: dict) -> SaleListing:
        item = SaleListing(**data)

        self.db.add(item)
        try:
            await self.db.commit()
            await self.db.refresh(item)
            return await self.get_listing_id(item.id)
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create listing")

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[SaleListing]:
        result = await self.db.execute(
            select(SaleListing).where(SaleListing.listed_by_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_address(self, address: str) -> SaleListing | None:
        result = await self.db.execute(
            select(SaleListing).where(SaleListing.address == address)
        )
        return result.scalar_one_or_none()

    async def update(self, listing_id: uuid.UUID, data: dict) -> Optional[SaleListing]:
        stmt = (
            update(SaleListing)
            .where(SaleListing.id == listing_id)
            .values(**data)
            .returning(SaleListing)
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

    async def get_by_id(self, listing_id: uuid.UUID) -> SaleListing | None:
        return await self.db.get(SaleListing, listing_id)

    async def get_all(
        self, page: int = 1, per_page: int = 20, is_available: bool = True
    ) -> List[SaleListing]:
        stmt = (
            select(SaleListing)
            .where(SaleListing.is_available == is_available)
            .options(
                selectinload(SaleListing.state),
                selectinload(SaleListing.lga),
                selectinload(SaleListing.seller),
                selectinload(SaleListing.gallery),
                selectinload(SaleListing.listed_by),
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_state(
        self,
        state_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        is_available: bool = True,
    ):
        stmt = (
            (
                select(SaleListing)
                .options(
                    selectinload(SaleListing.state),
                    selectinload(SaleListing.lga),
                    selectinload(SaleListing.seller),
                    selectinload(SaleListing.gallery),
                    selectinload(SaleListing.listed_by),
                )
                .where(
                    SaleListing.state_id == state_id,
                    SaleListing.is_available == is_available,
                )
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_lga(
        self,
        lga_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        is_available: bool = True,
    ):
        stmt = (
            (
                select(SaleListing)
                .options(
                    selectinload(SaleListing.state),
                    selectinload(SaleListing.lga),
                    selectinload(SaleListing.seller),
                    selectinload(SaleListing.gallery),
                    selectinload(SaleListing.listed_by),
                )
                .where(
                    SaleListing.lga_id == lga_id,
                    SaleListing.is_available == is_available,
                )
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_sold_properties(
        self, user_id: uuid.UUID, page=1, per_page=20, is_available: bool = False
    ):
        stmt = (
            select(SaleListing)
            .where(
                SaleListing.listed_by_id == user_id,
                SaleListing.is_available == is_available,
            )
            .options(
                selectinload(SaleListing.state),
                selectinload(SaleListing.lga),
                selectinload(SaleListing.gallery),
                selectinload(SaleListing.seller),
                selectinload(SaleListing.listed_by),
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete(
        self,
        listing_id: uuid.UUID,
        user_id: uuid.UUID,
        is_available: bool = True,
    ):
        stmt = await self.db.execute(
            delete(SaleListing).where(
                SaleListing.id == listing_id,
                SaleListing.listed_by_id == user_id,
                SaleListing.is_available == is_available,
            )
        )

        try:
            await self.db.commit()
            return stmt.rowcount

        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to delete listing")

    async def delete_all(self) -> SaleListing:
        stmt = delete(SaleListing)
        result = await self.db.execute(stmt)
        try:
            await self.db.commit()
            return result.rowcount
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to delete all listings")
