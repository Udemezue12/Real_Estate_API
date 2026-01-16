import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from models.enums import RentCycle
from models.models import Property, Tenant, User, RentReceipt
from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload


class TenantRepo:
    def __init__(self, db):
        self.db = db

    async def get_by_phoneNumber(self, phone_number: str) -> Tenant | None:
        result = await self.db.execute(
            select(Tenant).where(Tenant.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: uuid.UUID) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.matched_user_id == user_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def tenant_exists(
        self,
        *,
        property_id: uuid.UUID,
        last_name: str,
        first_name: str,
        is_active: bool = True,
    ) -> bool:
        stmt = select(Tenant.id).where(
            Tenant.property_id == property_id,
            Tenant.first_name == first_name,
            Tenant.last_name == last_name,
            Tenant.is_active == is_active,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create(self, tenant_data: dict) -> Tenant:
        try:
            stmt = insert(Tenant).values(**tenant_data).returning(Tenant)
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.scalar_one()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def update(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        new_rent_amount: Decimal | None = None,
        new_rent_cycle: RentCycle | None = None,
        new_rent_start_date: date | None = None,
        new_rent_expiry_date: date | None = None,
    ) -> Optional[Tenant]:
        values = {}
        if new_rent_amount is not None:
            values["rent_amount"] = new_rent_amount
        if new_rent_cycle is not None:
            values["rent_cycle"] = new_rent_cycle
        if new_rent_start_date is not None:
            values["rent_start_date"] = new_rent_start_date
        if new_rent_expiry_date is not None:
            values["rent_expiry_date"] = new_rent_expiry_date

        stmt = (
            update(Tenant)
            .where(Tenant.id == tenant_id, Tenant.matched_user_id == user_id)
            .values(**values)
            .returning(Tenant)
        )

        result = await self.db.execute(stmt)
        updated = result.scalar_one_or_none()
        return updated

    async def delete(self, tenant_id: uuid.UUID) -> int:
        try:
            stmt = delete(Tenant).where(Tenant.id == tenant_id)
            result = await self.db.execute(stmt)

            await self.db.commit()
            return result.rowcount
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_matched_id(self, matched_user_id: uuid.UUID) -> Optional[Tenant]:
        stmt = select(Tenant).where(Tenant.matched_user_id == matched_user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_by_property(
        self, property_id: uuid.UUID, offset: int = 0, limit: int = 100
    ) -> List[Tenant]:
        stmt = (
            select(Tenant)
            .options(
                selectinload(Tenant.property),
                selectinload(Tenant.rent_receipts).selectinload(
                    RentReceipt.payment_proof
                ),
            )
            .where(Tenant.property_id == property_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_with_property(self, tenant_id: uuid.UUID) -> Tenant | None:
        stmt = (
            select(Tenant)
            .options(selectinload(Tenant.property))
            .where(Tenant.id == tenant_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, offset: int = 0, limit: int = 100) -> List[Tenant]:
        stmt = (
            select(Tenant)
            .options(
                selectinload(Tenant.property),
                selectinload(Tenant.rent_receipts).selectinload(
                    RentReceipt.payment_proof
                ),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_property_and_name(
        self,
        property_id: uuid.UUID,
        first_name: str | None = None,
        last_name: str | None = None,
    ):
        stmt = select(Tenant).where(Tenant.property_id == property_id)
        if first_name:
            stmt = stmt.where(Tenant.first_name == first_name)
        if last_name:
            stmt = stmt.where(Tenant.last_name == last_name)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_tenant_with_details(self, tenant_id: uuid.UUID) -> Tenant | None:
        stmt = (
            select(Tenant)
            .where(Tenant.id == tenant_id)
            .options(
                selectinload(Tenant.rent_receipts).selectinload(
                    RentReceipt.payment_proof
                ),
               
                selectinload(Tenant.property).selectinload(Property.managed_by),
                selectinload(Tenant.property).selectinload(Property.state),
                selectinload(Tenant.property).selectinload(Property.lga),
                selectinload(Tenant.property).selectinload(Property.images),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_property(self, property_id: uuid.UUID) -> Property:
        stmt = (
            select(Property)
            .where(Property.id == property_id)
            .options(
                selectinload(Property.managed_by),
                selectinload(Property.state),
                selectinload(Property.lga),
                selectinload(Property.images),
            )
        )
        result = await self.db.execute(stmt)
        prop = result.scalar_one_or_none()

        return prop

    async def find_unmatched_by_name(self, first_name, last_name, middle_name):
        stmt = select(Tenant).where(
            Tenant.matched_user_id.is_(None),
            func.lower(Tenant.first_name) == first_name.lower(),
            func.lower(Tenant.middle_name) == middle_name.lower(),
            func.lower(Tenant.last_name) == last_name.lower(),
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def attach_user(self, tenant: Tenant | None, user: User):
        try:
            if tenant is None or user is None:
                return
            tenant.matched_user_id = user.id
            if user.phone_number is not None:
                tenant.phone_number = user.phone_number
            tenant.is_active = True
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise

    async def get_tenants_expiring_in(self, days: int) -> Tenant:
        target_date = date.today() + timedelta(days=days)

        stmt = (
            select(Tenant)
            .where(Tenant.is_active == True)
            .where(Tenant.rent_expiry_date == target_date)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_expired_active_tenants(self):
        stmt = (
            select(Tenant)
            .where(Tenant.is_active == True)
            .where(Tenant.rent_expiry_date < date.today())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def deactivate(self, tenant: Tenant):
        try:
            tenant.is_active = False
            self.db.add(tenant)
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def db_commit(self):
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def db_commit_and_refresh(self, value):
        try:
            await self.db.commit()
            await self.db.refresh(value)
        except SQLAlchemyError:
            await self.db.rollback()
            raise
