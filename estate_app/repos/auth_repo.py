import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from models.models import BlacklistedToken, User


class AuthRepo:
    def __init__(self, db):
        self.db = db

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_firstName(self, first_name: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.first_name == first_name)
        )
        return result.scalar_one_or_none()

    async def by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_current_user(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def get_by_lastName(self, last_name: str) -> User | None:
        result = await self.db.execute(select(User).where(User.last_name == last_name))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        email_payload = email.strip().lower()
        result = await self.db.execute(select(User).where(User.email == email_payload))
        return result.scalar_one_or_none()

    async def get_by_phoneNumber(self, phone_number: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def find_users_by_name_strict(self, name: str) -> list[User]:
        parts = name.strip().split()
        if len(parts) != 3:
            return []

        first, middle, last = parts

        stmt = select(User).where(
            func.lower(User.first_name) == first.lower(),
            func.lower(User.middle_name) == middle.lower(),
            func.lower(User.last_name) == last.lower(),
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, user: User) -> User:
        if user.id is not None:
            raise ValueError(
                "create() called with existing user — use update() instead"
            )
        self.db.add(user)
        return await self._commit_and_refresh(user)

    async def update(self, user: User) -> User:
        if user.id is None:
            raise ValueError("update() called with no ID — use create() instead")

        self.db.add(user)
        return await self._commit_and_refresh(user)

    async def save(self, user: User) -> User:
        self.db.add(user)
        return await self._commit_and_refresh(user)

    async def _commit_and_refresh(self, user: User) -> User:
        try:
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    

    async def blacklist_token(self, token: str):
        stmt = (
            insert(BlacklistedToken)
            .values(token=token)
            .on_conflict_do_nothing(index_elements=["token"])
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def is_token_blacklisted(self, token: str) -> bool:
        result = await self.db.execute(
            select(BlacklistedToken).where(BlacklistedToken.token == token)
        )
        return result.scalar_one_or_none() is not None

    async def delete_expired_blacklisted_tokens(self, cutoff: datetime):
        try:
            await self.db.execute(
                delete(BlacklistedToken).where(BlacklistedToken.blacklisted_on < cutoff)
            )
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise
