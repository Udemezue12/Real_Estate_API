import uuid
from typing import Optional

from sqlalchemy import or_, select, update
from sqlalchemy.exc import SQLAlchemyError

from core.normalizer import get_canonical_bank_name
from models.models import Bank


class BankRepo:
    def __init__(self, db):
        self.db = db

    async def get_banks(self, page: int = 1, per_page: int = 20) -> list[Bank]:
        result = await self.db.execute(
            select(Bank)
            .order_by(Bank.name)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return result.scalars().all()

    async def create_or_update(
        self,
        *,
        name: str,
        canonical_name: str,
        paystack_bank_code: str | None = None,
        flutterwave_bank_code: str | None = None,
    ) -> Bank:
        bank = await self.get_name(name)

        try:
            if not bank:
                bank = Bank(
                    name=name,
                    canonical_name=canonical_name,
                    paystack_bank_code=paystack_bank_code,
                    flutterwave_bank_code=flutterwave_bank_code,
                )
                self.db.add(bank)
            else:
                if paystack_bank_code is not None:
                    bank.paystack_bank_code = paystack_bank_code
                if flutterwave_bank_code is not None:
                    bank.flutterwave_bank_code = flutterwave_bank_code

            await self.db.commit()
            await self.db.refresh(bank)
            return bank

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def needs_sync(self) -> bool:
        result = await self.db.execute(
            select(Bank).where(
                or_(
                    Bank.paystack_bank_code.is_(None),
                    Bank.flutterwave_bank_code.is_(None),
                )
            )
        )
        return result.first() is not None

    async def update_paystack_bank_code(self, bank_id: uuid.UUID, bank_code: str):
        await self.db.execute(
            update(Bank).where(Bank.id == bank_id).values(paystack_bank_code=bank_code)
        )

        await self.db_commit()

    async def update_flutterwave_bank_code(self, bank_id: uuid.UUID, bank_code: str):
        await self.db.execute(
            update(Bank)
            .where(Bank.id == bank_id)
            .values(flutterwave_bank_code=bank_code)
        )
        await self.db_commit()

    async def get_by_id(self, bank_id: uuid.UUID) -> Bank | None:
        result = await self.db.execute(select(Bank).where(Bank.id == bank_id))
        return result.scalar_one_or_none()

    async def get_by_user_input(self, user_input: str) -> Bank | None:
        canonical = get_canonical_bank_name(user_input)

        result = await self.db.execute(
            select(Bank).where(Bank.canonical_name == canonical)
        )
        return result.scalar_one_or_none()

    async def get_name(self, name: str) -> Optional[Bank]:
        result = await self.db.execute(select(Bank).where(Bank.name == name))
        return result.scalar_one_or_none()

    async def get_all_banks(self) -> list[Bank]:
        result = await self.db.execute(
            select(Bank)
            .order_by(Bank.name)
            
        )
        return result.scalars().all()

    async def update(
        self, bank_id: uuid.UUID, new_name: str | None = None
    ) -> Optional[Bank]:
        values = {}
        if new_name is not None:
            values["name"] = new_name

        stmt = update(Bank).where(Bank.id == bank_id).values(**values).returning(Bank)

        result = await self.db.execute(stmt)
        updated = result.scalar_one_or_none()
        return updated

    async def db_commit(self):
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise
