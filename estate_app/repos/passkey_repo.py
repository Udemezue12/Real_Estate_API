import uuid

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from models.models import PasskeyCredential, User


class PasskeyRepo:
    def __init__(self, db):
        self.db = db

    async def get_all_passkeys_for_user(
        self, user_id: uuid.UUID, page: int = 1, per_page: int = 20
    ) -> list[PasskeyCredential]:
        result = await self.db.execute(
            select(PasskeyCredential)
            .where(PasskeyCredential.user_id == user_id)
            .order_by(PasskeyCredential.credential_id)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return result.scalars().all()

    async def get_passkey_by_id_for_user(
        self,
        *,
        user_id: uuid.UUID,
        passkey_id: uuid.UUID,
    ) -> PasskeyCredential:
        result = await self.db.execute(
            select(PasskeyCredential).where(
                (PasskeyCredential.id == passkey_id)
                & (PasskeyCredential.user_id == user_id)
            )
        )

        passkey = result.scalars().first()

        return passkey

    async def get_credential_id(
        self, user_id: uuid.UUID, credential_id: str
    ) -> PasskeyCredential:
        result = await self.db.execute(
            select(PasskeyCredential).where(
                (PasskeyCredential.user_id == user_id)
                & (PasskeyCredential.credential_id == credential_id)
            )
        )
        return result.scalar_one_or_none()

    async def update_sign_count(
        self,
        *,
        credential_id: uuid.UUID,
        new_sign_count: int,
    ):
        try:
            stmt = (
                update(PasskeyCredential)
                .where(PasskeyCredential.id == credential_id)
                .values(sign_count=new_sign_count)
            )
            await self.db.execute(stmt)
            await self.db.commit()
            await self.db.refresh(stmt)
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(500, "Could not Update")

    async def get_credentials(
        self, page: int = 1, per_page: int = 20
    ) -> PasskeyCredential:
        result = await self.db.execute(
            select(PasskeyCredential)
            .order_by(PasskeyCredential.credential_id)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return result.scalars().all()

    async def get_registered_passkeys(
        self, user_id: uuid.UUID, page: int = 1, per_page: int = 20
    ) -> list[PasskeyCredential]:
        result = await self.db.execute(
            select(PasskeyCredential)
            .where(PasskeyCredential.user_id == user_id)
            .order_by(PasskeyCredential.credential_id)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return result.scalars().all()

    async def get_public_key(self, user_id: uuid.UUID, public_key: str):
        result = await self.db.execute(
            select(PasskeyCredential).where(
                (PasskeyCredential.user_id == user_id)
                & (PasskeyCredential.public_key == public_key)
            )
        )
        return result.scalars().first()

    async def get_device_fingerprint(self, user_id: uuid.UUID, device_fingerprint: str):
        result = await self.db.execute(
            select(PasskeyCredential).where(
                (PasskeyCredential.device_fingerprint == device_fingerprint)
                & (PasskeyCredential.user_id != user_id)
            )
        )
        return result.scalars().first()

    async def get_valid_credential_id(self, credential_id: str) -> PasskeyCredential:
        result = await self.db.execute(
            select(PasskeyCredential).where(
                PasskeyCredential.credential_id == credential_id
            )
        )
        return result.scalars().first()

    async def get_user_passkey_by_id(self, user_id: uuid.UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def create_passkey(
        self,
        credential_id: str,
        device_fingerprint: str,
        user_id: int,
        public_key: str,
        sign_count: int,
    ) -> PasskeyCredential:
        new_cred = PasskeyCredential(
            credential_id=credential_id,
            device_fingerprint=device_fingerprint,
            user_id=user_id,
            public_key=public_key,
            sign_count=sign_count,
        )
        self.db.add(new_cred)

        try:
            await self.db.commit()
            await self.db.refresh(new_cred)
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(500, "Could not save passkey")

    async def delete_passkey_by_id(
        self,
        *,
        user_id: uuid.UUID,
        passkey_id: uuid.UUID,
    ) -> None:
        result = await self.db.execute(
            select(PasskeyCredential).where(
                (PasskeyCredential.id == passkey_id)
                & (PasskeyCredential.user_id == user_id)
            )
        )

        passkey = result.scalars().first()

        if not passkey:
            raise HTTPException(404, "Passkey not found")

        try:
            await self.db.delete(passkey)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(500, "Failed to delete passkey")
