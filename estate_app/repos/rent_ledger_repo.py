from sqlalchemy import select
from models.models import RentLedger
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID


class RentLedgerRepository:
    def __init__(self, db):
        self.db = db

    async def create(
        self,
        tenant_id: UUID,
        event: str,
        old_value: dict | None=None,
        new_value: dict | None=None,
    ):
        try:
            ledger = RentLedger(
                tenant_id=tenant_id,
                event=event,
                old_value=old_value,
                new_value=new_value,
            )
            self.db.add(ledger)
            await self.db.commit()
            await self.db.refresh(ledger)
            return ledger
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def exists(self, tenant_id: UUID, event: str) -> bool:
        stmt = select(RentLedger.id).where(
            RentLedger.tenant_id == tenant_id,
            RentLedger.event == event,
        )
        result = await self.db.execute(stmt)
        return result.first() is not None
