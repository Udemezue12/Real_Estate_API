import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from models.enums import SOLD_BY
from models.models import SaleListing


class SaleListingRepo:
    def __init__(self, db):
        self.db = db

    async def mark_as_sold(
        self,
        listing_id: uuid.UUID,
        user_id: uuid.UUID,
        sold_by: SOLD_BY,
        is_available: bool,
    ):
        stmt = (
            update(SaleListing)
            .where(
                SaleListing.id == listing_id,
                SaleListing.listed_by_id == user_id,
                SaleListing.is_available == is_available,
            )
            .values(is_available=is_available, sold_by=sold_by)
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

    async def mark_property_verified(self, property_id: uuid.UUID, is_verified: bool):
        stmt = (
            update(SaleListing)
            .where(SaleListing.id == property_id)
            .values(is_verified=is_verified)
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
            return await self.get_listing_id(property_id)
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_listing_id(self, listing_id: uuid.UUID) -> SaleListing:
        stmt = (
            select(SaleListing)
            .options(
                selectinload(SaleListing.gallery),
                selectinload(SaleListing.state),
                selectinload(SaleListing.lga),
                selectinload(SaleListing.seller),
                selectinload(SaleListing.listed_by),
            )
            .where(SaleListing.id == listing_id)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

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

    async def get_property_with_relations(
        self, listing_id: uuid.UUID
    ) -> Optional[SaleListing]:
        result = await self.db.execute(
            select(SaleListing)
            .options(
                selectinload(SaleListing.gallery),
                selectinload(SaleListing.state),
                selectinload(SaleListing.lga),
                selectinload(SaleListing.seller),
                selectinload(SaleListing.listed_by),
            )
            .where(SaleListing.id == listing_id)
        )
        return result.scalars().first()

    async def fetch_sale_listing(self, listing_id: uuid.UUID) -> Optional[SaleListing]:
        stmt = select(SaleListing).where(SaleListing.id == listing_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self,
        user_id: uuid.UUID,
        listing_id: uuid.UUID,
        *,
        plot_size: Decimal | None = None,
        title: str | None = None,
        description: str | None = None,
        address: str | None = None,
        parking_spaces: int | None = None,
        price: Decimal | None = None,
        bathrooms: int | None = None,
        toilets: int | None = None,
        state_id: uuid.UUID | None = None,
        lga_id: uuid.UUID | None = None,
        updated_at: datetime | None = None,
        contact_phone: str | None = None,
    ):
        property_obj = await self.fetch_sale_listing(listing_id=listing_id)
        print("returned:", property_obj)
        print("returned type:", type(property_obj))
        if not isinstance(property_obj, SaleListing):
            raise RuntimeError(f"Expected SaleListing, got {type(property_obj)}")

        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found.")
        if property_obj.listed_by_id != user_id:
            raise HTTPException(403, "You are not allowed to update this property")
        if contact_phone is not None:
            property_obj.contact_phone = contact_phone
        if price is not None:
            property_obj.price = price
        if plot_size is not None:
            property_obj.plot_size = plot_size
        if updated_at is not None:
            property_obj.updated_at = updated_at

        if parking_spaces is not None:
            property_obj.parking_spaces = parking_spaces

        if address is not None and address != property_obj.address:
            property_obj.address = address

        if title is not None:
            property_obj.title = title

        if description is not None:
            property_obj.description = description

        if bathrooms is not None:
            property_obj.bathrooms = bathrooms

        if toilets is not None:
            property_obj.toilets = toilets

        if lga_id is not None:
            property_obj.lga_id = lga_id
        if state_id is not None:
            property_obj.state_id = state_id

        try:
            await self.db.commit()
            await self.db.refresh(property_obj)
            return property_obj
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_all(
        self,
        page: int = 1,
        per_page: int = 20,
        is_available: bool = True,
        is_verified: bool = True,
    ) -> List[SaleListing]:
        stmt = (
            select(SaleListing)
            .where(
                SaleListing.is_available == is_available,
                SaleListing.is_verified == is_verified,
            )
            .options(
                selectinload(SaleListing.state),
                selectinload(SaleListing.lga),
                selectinload(SaleListing.seller),
                selectinload(SaleListing.gallery),
                selectinload(SaleListing.listed_by),
            )
            .order_by(SaleListing.id)
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
        is_verified: bool = True,
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
                    SaleListing.is_verified == is_verified,
                )
            )
            .order_by(SaleListing.id)
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
        is_verified: bool = True,
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
                    SaleListing.is_verified == is_verified,
                )
            )
            .order_by(SaleListing.id)
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
            .order_by(SaleListing.id)
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
