import uuid
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from models.enums import PaymentProvider, PaymentStatus
from models.models import PaymentTransaction


class PaymentTransactionRepo:
    def __init__(self, db):
        self.db = db

    async def get_reference(self, reference: str) -> PaymentTransaction | None:
        result = await self.db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.provider_reference == reference
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        tenant_id: uuid.UUID,
        property_id: uuid.UUID,
        owner_id: uuid.UUID,
        landlord_profile_id:uuid.UUID,
        payment_provider: PaymentProvider,
        amount: Decimal,
        status: PaymentStatus,
        tenant_email: str,
        landlord_email: str,
        landlord_id:uuid.UUID,
        landlord_firstname: str,
        landlord_lastname: str,
        landlord_middlename: str,
        tenant_firstname: str,
        tenant_lastname: str,
        tenant_middlename: str,
        tenant_phoneNumber:str,
        landlord_phoneNumber:str,
        currency: str = "Naira",

    ):
        payment = PaymentTransaction(
            tenant_id=tenant_id,
            property_id=property_id,
            payment_provider=payment_provider,
            amount_received=amount,
            currency=currency,
            status=status,
            property_owner_id=owner_id,
            landlord_profile_id=landlord_profile_id,
            tenant_email=tenant_email,
            landlord_email=landlord_email,
            landlord_firstname=landlord_firstname,
            landlord_lastname=landlord_lastname,
            landlord_middlename=landlord_middlename,
            tenant_firstname=tenant_firstname,
            tenant_lastname=tenant_lastname,
            tenant_middlename=tenant_middlename,
            tenant_phoneNumber=tenant_phoneNumber,
            landlord_phoneNumber=landlord_phoneNumber,
            landlord_id=landlord_id

        )
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)

        return payment


    async def update_status_provider(
        self,
        payment_id: uuid.UUID,
        status: PaymentStatus,
        payment_provider: PaymentProvider,
    ):
        stmt = (
            update(PaymentTransaction)
            .where(PaymentTransaction.id == payment_id)
            .values(status=status, payment_provider=payment_provider)
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def update_status(self, payment_id: uuid.UUID, status: PaymentStatus):
        stmt = (
            update(PaymentTransaction)
            .where(PaymentTransaction.id == payment_id)
            .values(status=status)
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_payment_id(self, payment_id: uuid.UUID) -> PaymentTransaction:
        result = await self.db.execute(
            select(PaymentTransaction)
            .options(
                selectinload(PaymentTransaction.tenant),
                selectinload(PaymentTransaction.property),
            )
            .where(PaymentTransaction.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def update_payment_id(
        self,
        payment_id: uuid.UUID,
        status: PaymentStatus,
        payment_provider: PaymentProvider,
    ):
        stmt = (
            update(PaymentTransaction)
            .where(PaymentTransaction.id == payment_id)
            .values(status=status, payment_provider=payment_provider)
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def set_reference(self, payment_id: uuid.UUID, reference: str):
        stmt = (
            update(PaymentTransaction)
            .where(PaymentTransaction.id == payment_id)
            .values(provider_reference=reference)
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def _commit_and_refresh(self, value):
        try:
            await self.db.commit()
            await self.db.refresh(value)
            return value
        except SQLAlchemyError:
            await self.db.rollback()
            raise
    async def db_commit(self):
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def db_add_and_flush(self, value):
        try:
            self.db.add(value)
            await self.db.flush()
            return value
        except SQLAlchemyError:
            await self.db.rollback()
            raise
    async def db_add_commit_and_flush(self, value):
        try:
            self.db.add(value)
            await self.db.flush()
            await self.db.refresh(value)
            return value
        except SQLAlchemyError:
            await self.db.rollback()
            raise
