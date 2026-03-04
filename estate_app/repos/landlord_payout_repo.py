from decimal import Decimal
from uuid import UUID

from models.enums import PayoutStatus
from models.models import LandlordPayout
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional

class LandLordPayoutRepo:
    def __init__(self, db):
        self.db = db

    async def get_landlord_payment_id(self, payment_id: UUID) -> LandlordPayout | None:
        payout = await self.db.execute(
            select(LandlordPayout).where(LandlordPayout.payment_id == payment_id)
        )
        return payout.scalar_one_or_none()
    def sync_landlord_payment_id(self, payment_id: UUID) -> LandlordPayout | None:
        payout = self.db.execute(
            select(LandlordPayout).where(LandlordPayout.payment_id == payment_id)
        )
        return payout.scalar_one_or_none()

    def create(
        self, payment_id: UUID, landlord_id: UUID, amount: Decimal, status: PayoutStatus
    ) -> LandlordPayout:
        payout = LandlordPayout(
            payment_id=payment_id, landlord_id=landlord_id, amount=amount, status=status
        )
        try:
            self.db.add(payout)
            self.db.commit()
            self.db.refresh(payout)
            return payout
        except SQLAlchemyError:
            self.db.rollback()
            raise
    async def get_payout_id(self, payout_id:UUID):
        result = await self.db.execute(
            select(LandlordPayout).where(LandlordPayout.id == payout_id)
        )

        return result.scalar_one_or_none()
    def update_status(
        self, payout_id: UUID, status: PayoutStatus
    ) -> LandlordPayout:
        stmt = (
            update(LandlordPayout)
            .where(LandlordPayout.id == payout_id)
            .values(status=status)
        )
        try:
            result = self.db.execute(stmt)
            self.db.commit()
            return result
            
        except SQLAlchemyError:
            self.db.rollback()
            raise

    async def add_commit_and_refresh(self, value):
        try:
            self.db.add(value)
            await self.db.commit()
            await self.db.refresh(value)
            return value
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def db_commit(
        self,
    ):
        try:
            await self.db.commit()
            

        except SQLAlchemyError:
            await self.db.rollback()
            raise
    def sync_db_commit(
        self,
    ):
        try:
            self.db.commit()
            

        except SQLAlchemyError:
            self.db.rollback()
            raise
