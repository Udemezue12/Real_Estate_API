import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models.models import IdempotencyKey


class IdempotencyRepo:
    def __init__(self, db):
        self.db = db

    async def get(self, key: str, user_id: uuid.UUID) -> IdempotencyKey | None:
        result = await self.db.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.key == key, IdempotencyKey.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def save(self, key: str, user_id: uuid.UUID, endpoint: str):
        record = IdempotencyKey(key=key, user_id=user_id, endpoint=endpoint)
        self.db.add(record)
        return await self._commit_and_refresh(record)

    async def store_response(self, key: str, response: dict, user_id: uuid.UUID):
        await self.db.execute(
            update(IdempotencyKey)
            .where(IdempotencyKey.key == key, IdempotencyKey.user_id == user_id)
            .values(response=response)
        )
        await self._commit()
        return await self.get(key=key, user_id=user_id)

    async def create_or_get(self, idem_key: str, user_id: uuid.UUID, endpoint: str):
        record = IdempotencyKey(
            key=idem_key,
            user_id=user_id,
            endpoint=endpoint,
        )

        self.db.add(record)

        try:
            await self.db.commit()
            await self.db.refresh(record)
            return record, True

        except IntegrityError:
            await self.db.rollback()

            existing = await self.get(idem_key, user_id)
            return existing, False

    async def _commit_and_refresh(self, idem: IdempotencyKey) -> IdempotencyKey:
        try:
            await self.db.commit()
            await self.db.refresh(idem)
            return idem
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def _commit(self):
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise
