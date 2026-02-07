import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from models.enums import (Furnishing, HouseType, PropertyTypes, RentCycle,
                          RentDuration)
from models.models import RentalListing


class RentalListingRepo:
    def __init__(self, db):
        self.db = db

    async def get_listing_id(self, listing_id: uuid.UUID) -> RentalListing:
        stmt = (
            select(RentalListing)
            .options(
                selectinload(RentalListing.gallery),
                selectinload(RentalListing.state),
                selectinload(RentalListing.lga),
                selectinload(RentalListing.renter),
                selectinload(RentalListing.listed_by),
            )
            .where(RentalListing.id == listing_id)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_property_with_relations(self, listing_id: uuid.UUID) -> RentalListing:
        result = await self.db.execute(
            select(RentalListing)
            .options(
                selectinload(RentalListing.gallery),
                selectinload(RentalListing.state),
                selectinload(RentalListing.lga),
                selectinload(RentalListing.renter),
                selectinload(RentalListing.listed_by),
            )
            .where(RentalListing.id == listing_id)
        )
        return result.scalars().first()

    async def mark_property_verified(
        self,
        property_id: uuid.UUID,
        verified_by_id: uuid.UUID,
        is_verified: bool = True,
        verified_at: datetime = datetime.utcnow(),
    ):
        stmt = (
            update(RentalListing)
            .where(RentalListing.id == property_id)
            .values(
                is_verified=is_verified,
                verified_by_id=verified_by_id,
                verified_at=verified_at,
            )
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
            return await self.get_listing_id(property_id)
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def create(self, data: dict) -> RentalListing:
        listing = RentalListing(**data)
        self.db.add(listing)

        try:
            await self.db.commit()
            await self.db.refresh(listing)
            return listing
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
        self,
        user_id: uuid.UUID,
        listing_id: uuid.UUID,
        *,
        has_electricity: bool | None = None,
        has_water: bool | None = None,
        title: str | None = None,
        description: str | None = None,
        address: str | None = None,
        rent_duration: RentDuration | None = None,
        furnished_level: Furnishing | None = None,
        house_type: HouseType | None = None,
        property_type: PropertyTypes | None = None,
        parking_spaces: int | None = None,
        toilets: int | None = None,
        rooms: int | None = None,
        bathrooms: int | None = None,
        rent_cycle: RentCycle | None = None,
        slug: str | None = None,
        rent_amount: Decimal | None = None,
        state_id: uuid.UUID | None = None,
        lga_id: uuid.UUID | None = None,
        expires_at: datetime | None = None,
    ):
        property_obj = await self.get_by_id(listing_id=listing_id)

        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found.")
        if property_obj.rental_listed_by != user_id:
            raise HTTPException(403, "You are not allowed to update this property")
        if expires_at is not None:
            property_obj.expires_at = expires_at
        if has_electricity is not None:
            property_obj.has_electricity = has_electricity
        if parking_spaces is not None:
            property_obj.parking_spaces = parking_spaces
        if slug is not None:
            property_obj.slug = slug
        if has_water is not None:
            property_obj.has_water = has_water
        if rent_duration is not None:
            property_obj.rent_duration = rent_duration
        if furnished_level is not None:
            property_obj.furnished_level = furnished_level

        if address is not None and address != property_obj.address:
            property_obj.address = address

        if title is not None:
            property_obj.title = title

        if description is not None:
            property_obj.description = description

        if rooms is not None:
            property_obj.rooms = rooms

        if bathrooms is not None:
            property_obj.bathrooms = bathrooms

        if toilets is not None:
            property_obj.toilets = toilets

        if rent_amount is not None:
            property_obj.rent_amount = rent_amount

        if rent_cycle is not None:
            property_obj.rent_cycle = rent_cycle

        if house_type is not None:
            property_obj.house_type = house_type

        if property_type is not None:
            property_obj.property_type = property_type

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

    async def get_by_id(self, listing_id: uuid.UUID) -> Optional[RentalListing]:
        stmt = select(RentalListing).where(RentalListing.id == listing_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        page: int = 1,
        per_page: int = 20,
        is_verified: bool = True,
        is_available: bool = True,
    ) -> List[RentalListing]:
        stmt = (
            select(RentalListing)
            .where(
                RentalListing.is_available == is_available,
                RentalListing.is_verified == is_verified,
            )
            .options(
                selectinload(RentalListing.state),
                selectinload(RentalListing.lga),
                selectinload(RentalListing.renter),
                selectinload(RentalListing.gallery),
                selectinload(RentalListing.listed_by),
            )
            .order_by(RentalListing.id)
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
        is_verified: bool = True,
        is_available: bool = True,
    ):
        stmt = (
            (
                select(RentalListing)
                .where(
                    RentalListing.is_available == is_available,
                    RentalListing.is_verified == is_verified,
                )
                .options(
                    selectinload(RentalListing.state),
                    selectinload(RentalListing.lga),
                    selectinload(RentalListing.renter),
                    selectinload(RentalListing.gallery),
                    selectinload(RentalListing.listed_by),
                )
                .where(RentalListing.state_id == state_id)
            )
            .order_by(RentalListing.id)
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
        is_verified: bool = True,
        is_available: bool = True,
    ):
        stmt = (
            (
                select(RentalListing)
                .where(
                    RentalListing.is_available == is_available,
                    RentalListing.is_verified == is_verified,
                )
                .options(
                    selectinload(RentalListing.state),
                    selectinload(RentalListing.lga),
                    selectinload(RentalListing.renter),
                    selectinload(RentalListing.gallery),
                    selectinload(RentalListing.listed_by),
                )
                .where(RentalListing.lga_id == lga_id)
            )
            .order_by(RentalListing.id)
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
            )
            .values(is_available=True, unavailable_at=datetime.utcnow())
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
