
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from models.models import RentInvoice


class RentInvoiceRepo:
    def __init__(self, db):
        self.db = db

    async def get_invoice_by_id(self, invoice_id: UUID) -> RentInvoice:
        exists = await self.db.execute(
            select(RentInvoice).where(RentInvoice.id == invoice_id)
        )
        return exists.scalar_one_or_none()
    

    async def add_commit_and_refresh(self, value):
        try:
            self.db.add(value)
            await self.db.commit()
            await self.db.refresh(value)
            return value
        except SQLAlchemyError:
            await self.db.rollback()
            raise
    async def commit_and_refresh(self, value):
        try:
            await self.db.commit()
            await self.db.refresh(value)
            return value
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def commit(
        self,
    ):
        try:
            await self.db.commit()
            await self.db.refresh()

        except SQLAlchemyError:
            await self.db.rollback()
            raise
