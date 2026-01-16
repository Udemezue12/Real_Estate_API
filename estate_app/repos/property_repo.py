import uuid
from typing import List, Optional

from core.geoapify import geocode_address
from fastapi import HTTPException
from geoalchemy2.shape import from_shape
from models.enums import HouseType, PropertyTypes
from models.models import Property
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError


class PropertyRepo:
    def __init__(self, db):
        self.db = db

    async def get_property_with_relations(self, property_id: uuid.UUID) -> Property:
        result = await self.db.execute(
            select(Property)
            .options(
                selectinload(Property.images),
                selectinload(Property.tenants),
                selectinload(Property.state),
                selectinload(Property.lga),
                selectinload(Property.rent_receipts),
                selectinload(Property.owner),
                selectinload(Property.managed_by),
            )
            .where(Property.id == property_id)
        )
        return result.scalars().first()

    async def get_by_address(self, address: str) -> Property | None:
        result = await self.db.execute(
            select(Property).where(Property.address == address)
        )
        return result.scalar_one_or_none()

    async def get_by_title(self, title: str) -> Property | None:
        result = await self.db.execute(select(Property).where(Property.title == title))
        return result.scalar_one_or_none()

    async def get_by_description(self, description: str) -> Property | None:
        result = await self.db.execute(
            select(Property).where(Property.description == description)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, property_id: uuid.UUID) -> Optional[Property]:
        result = await self.db.execute(
            select(Property).where(Property.id == property_id)
        )
        return result.scalar_one_or_none()

    async def get_one(self, property_id: uuid.UUID):
        query = (
            select(Property)
            .options(
                selectinload(Property.images),
                selectinload(Property.tenants),
                selectinload(Property.rent_receipts),
            )
            .where(Property.id == property_id)
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def create_first(
        self,
        owner_id: uuid.UUID,
        state_id: uuid.UUID,
        lga_id: uuid.UUID,
        title: str,
        description: str,
        address: str,
        rooms: int,
        bathrooms: int,
        toilets: int,
        default_rent_amount: int,
        default_rent_cycle: str,
        house_type: HouseType,
        property_type: PropertyTypes,
        square_meters: int,
        is_owner: bool,
        is_manager: bool,
        managed_by_id: uuid.UUID,
    ):
        new_property = Property(
            state_id=state_id,
            lga_id=lga_id,
            owner_id=owner_id,
            title=title,
            description=description,
            address=address,
            rooms=rooms,
            bathrooms=bathrooms,
            toilets=toilets,
            default_rent_amount=default_rent_amount,
            default_rent_cycle=default_rent_cycle,
            house_type=house_type,
            property_type=property_type,
            square_meters=square_meters,
            is_owner=is_owner,
            is_manager=is_manager,
            managed_by_id=managed_by_id,
        )
        self.db.add(new_property)
        try:
            await self.db.commit()
            await self.db.refresh(new_property)
            return new_property
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def update(
        self,
        user_id: uuid.UUID,
        property_id: uuid.UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        address: str | None = None,
        rooms: int | None = None,
        bathrooms: int | None = None,
        toilets: int | None = None,
        default_rent_amount: int | None = None,
        default_rent_cycle: str | None = None,
        house_type: HouseType | None = None,
        property_type: PropertyTypes | None = None,
        square_meters: int | None = None,
        is_owner: bool | None = None,
        is_manager: bool | None = None,
        managed_by_id: uuid.UUID | None = None,
    ):
        property_obj = await self.get_by_id(property_id=property_id)

        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found.")
        if property_obj.owner_id != user_id:
            raise HTTPException(403, "You are not allowed to update this property")

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

        if default_rent_amount is not None:
            property_obj.default_rent_amount = default_rent_amount

        if default_rent_cycle is not None:
            property_obj.default_rent_cycle = default_rent_cycle

        if house_type is not None:
            property_obj.house_type = house_type

        if property_type is not None:
            property_obj.property_type = property_type

        if square_meters is not None:
            property_obj.square_meters = square_meters

        if is_owner is not None:
            property_obj.is_owner = is_owner

        if is_manager is not None:
            property_obj.is_manager = is_manager

        if managed_by_id is not None:
            property_obj.managed_by_id = managed_by_id

        try:
            await self.db.commit()
            await self.db.refresh(property_obj)
            return property_obj
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def delete_property(
        self, user_id: uuid.UUID, property_id: uuid.UUID
    ) -> Property:
        try:
            result = await self.db.execute(
                delete(Property).where(
                    Property.id == property_id, Property.owner_id == user_id
                )
            )
            await self.db.commit()

            return result.rowcount

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_all(self) -> list[Property]:
        result = await self.db.execute(select(Property))
        return result.scalars().all()

    async def get_all_by_user(self, user_id: uuid.UUID) -> List[Property]:
        query = select(Property).where(Property.owner_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_all_properties(self) -> List[Property]:
        result = await self.db.execute(
            select(Property).options(
                selectinload(Property.images),
                selectinload(Property.tenants),
                selectinload(Property.state),
                selectinload(Property.lga),
                selectinload(Property.rent_receipts),
                selectinload(Property.owner),
                selectinload(Property.managed_by),
            )
        )
        return result.scalars().all()

    async def get_property_by_id(self, property_id: uuid.UUID) -> Optional[Property]:
        result = await self.db.execute(
            select(Property)
            .options(
                selectinload(Property.images),
                selectinload(Property.tenants),
                selectinload(Property.state),
                selectinload(Property.lga),
                selectinload(Property.rent_receipts),
                selectinload(Property.owner),
                selectinload(Property.managed_by),
            )
            .where(Property.id == property_id)
        )
        return result.scalars().first()

    async def get_properties_by_state_user(
        self, state_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[Property]:
        result = await self.db.execute(
            select(Property)
            .options(
                selectinload(Property.images),
                selectinload(Property.tenants),
                selectinload(Property.state),
                selectinload(Property.lga),
                selectinload(Property.rent_receipts),
                selectinload(Property.owner),
                selectinload(Property.managed_by),
            )
            .where(
                Property.state_id == state_id,
                (Property.owner_id == user_id) | (Property.managed_by_id == user_id),
            )
        )
        return result.scalars().all()

    async def get_property_by_state_user(
        self, state_id: uuid.UUID, property_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Property]:
        result = await self.db.execute(
            select(Property)
            .options(
                selectinload(Property.images),
                selectinload(Property.tenants),
                selectinload(Property.state),
                selectinload(Property.lga),
                selectinload(Property.rent_receipts),
                selectinload(Property.owner),
                selectinload(Property.managed_by),
            )
            .where(
                Property.id == property_id,
                Property.state_id == state_id,
                (Property.owner_id == user_id) | (Property.managed_by_id == user_id),
            )
        )
        return result.scalar_one_or_none()

    async def get_properties_by_lga_user(
        self, lga_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[Property]:
        result = await self.db.execute(
            select(Property)
            .options(
                selectinload(Property.images),
                selectinload(Property.tenants),
                selectinload(Property.state),
                selectinload(Property.lga),
                selectinload(Property.rent_receipts),
                selectinload(Property.owner),
                selectinload(Property.managed_by),
            )
            .where(
                Property.lga_id == lga_id,
                (Property.owner_id == user_id) | (Property.managed_by_id == user_id),
            )
        )
        return result.scalars().all()

    async def get_property_by_lga_user(
        self, lga_id: uuid.UUID, property_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Property]:
        result = await self.db.execute(
            select(Property)
            .options(
                selectinload(Property.images),
                selectinload(Property.tenants),
                selectinload(Property.state),
                selectinload(Property.lga),
                selectinload(Property.rent_receipts),
                selectinload(Property.owner),
                selectinload(Property.managed_by),
            )
            .where(
                Property.id == property_id,
                Property.lga_id == lga_id,
                (Property.owner_id == user_id) | (Property.managed_by_id == user_id),
            )
        )
        return result.scalar_one_or_none()
