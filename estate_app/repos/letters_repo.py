import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from models.enums import LetterType
from models.models import Letter, LetterRecipient
from repos.tenant_repo import TenantRepo


class LetterRepo:
    def __init__(self, db):
        self.db = db
        self.tenant_repo: TenantRepo = TenantRepo(db)

    async def get_all_landlord_letters(
        self, user_id: uuid.UUID, page: int = 1, per_page=20
    ) -> list[Letter]:
        result = await self.db.execute(
            select(Letter)
            .where(Letter.owner_id == user_id)
            .options(
                selectinload(Letter.sender),
                selectinload(Letter.property),
                selectinload(Letter.recipients),
            )
            .order_by(Letter.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return result.scalars().all()

    async def get_all_properties_letters(
        self, user_id: uuid.UUID, property_id: uuid.UUID, page: int = 1, per_page=20
    ) -> list[Letter]:
        result = await self.db.execute(
            select(Letter)
            .where(or_(Letter.owner_id == user_id, Letter.caretaker_id == user_id))
            .where(Letter.property_id == property_id)
            .options(
                selectinload(Letter.sender),
                selectinload(Letter.property),
                selectinload(Letter.recipients),
            )
            .order_by(Letter.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return result.scalars().all()

    async def get_single_letter_landlord(
        self,
        user_id: uuid.UUID,
        letter_id: uuid.UUID,
    ) -> Optional[Letter]:
        result = await self.db.execute(
            select(Letter)
            .where(Letter.owner_id == user_id, Letter.id == letter_id)
            .options(
                selectinload(Letter.sender),
                selectinload(Letter.property),
                selectinload(Letter.recipients),
            )
        )
        return result.scalar_one_or_none()

    async def get_single_property_letter(
        self,
        user_id: uuid.UUID,
        property_id: uuid.UUID,
        letter_id: uuid.UUID,
    ) -> Optional[Letter]:
        result = await self.db.execute(
            select(Letter)
            .where(
                (Letter.owner_id == user_id) | (Letter.caretaker_id == user_id),
                Letter.id == letter_id,
                Letter.property_id == property_id,
            )
            .options(
                selectinload(Letter.sender),
                selectinload(Letter.property),
                selectinload(Letter.recipients),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        letter_id: uuid.UUID,
    ) -> Optional[Letter]:
        result = await self.db.execute(
            select(Letter)
            .where(Letter.id == letter_id)
            .options(
                selectinload(Letter.sender),
                selectinload(Letter.property),
                selectinload(Letter.recipients),
            )
        )
        return result.scalar_one_or_none()

    async def get_owner_id(
        self,
        owner_id: uuid.UUID,
    ) -> Optional[Letter]:
        result = await self.db.execute(
            select(Letter)
            .where(Letter.owner_id == owner_id)
            .options(
                selectinload(Letter.sender),
                selectinload(Letter.property),
                selectinload(Letter.recipients),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_tenant_letters(
        self, tenant_id: uuid.UUID, page: int = 1, per_page=20
    ) -> list[LetterRecipient]:
        result = await self.db.execute(
            select(LetterRecipient)
            .where(LetterRecipient.tenant_id == tenant_id)
            .options(
                selectinload(LetterRecipient.letter),
                selectinload(LetterRecipient.tenant),
                selectinload(LetterRecipient.property),
            )
            .order_by(LetterRecipient.delivered_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return result.scalars().all()

    async def get_single_letter_tenant(
        self,
        tenant_id: uuid.UUID,
        recipient_letter_id: uuid.UUID,
    ) -> Optional[LetterRecipient]:
        result = await self.db.execute(
            select(LetterRecipient)
            .where(
                LetterRecipient.tenant_id == tenant_id,
                LetterRecipient.id == recipient_letter_id,
            )
            .options(
                selectinload(LetterRecipient.letter),
                selectinload(LetterRecipient.tenant),
                selectinload(LetterRecipient.property),
            )
        )
        return result.scalar_one_or_none()

    async def get_recipient_letter_id(
        self,
        recipient_letter_id: uuid.UUID,
    ) -> Optional[LetterRecipient]:
        result = await self.db.execute(
            select(LetterRecipient)
            .where(
                LetterRecipient.id == recipient_letter_id,
            )
            .options(
                selectinload(LetterRecipient.letter),
                selectinload(LetterRecipient.tenant),
                selectinload(LetterRecipient.property),
            )
        )
        return result.scalar_one_or_none()

    async def create_without_upload(
        self,
        sender_id: uuid.UUID,
        property_id: uuid.UUID,
        caretaker_id: uuid.UUID,
        owner_id: uuid.UUID,
        letter_type: LetterType,
        title: str,
        body: str,
    ):
        try:
            letter = Letter(
                sender_id=sender_id,
                owner_id=owner_id,
                property_id=property_id,
                caretaker_id=caretaker_id,
                letter_type=letter_type,
                title=title,
                body=body,
                file_path=None,
                public_id=None,
                file_hash=None,
                created_at=datetime.utcnow(),
            )
            self.db.add(letter)
            await self.db.flush()
            return letter
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def create_with_upload(
        self,
        sender_id: uuid.UUID,
        property_id: uuid.UUID,
        caretaker_id: uuid.UUID,
        letter_type: LetterType,
        title: str,
        file_hash: str,
        public_id: str,
        file_path: str,
        owner_id: uuid.UUID,
    ):
        try:
            letter = Letter(
                sender_id=sender_id,
                property_id=property_id,
                letter_type=letter_type,
                caretaker_id=caretaker_id,
                owner_id=owner_id,
                title=title,
                body=None,
                file_path=file_path,
                public_id=public_id,
                file_hash=file_hash,
                created_at=datetime.utcnow(),
            )
            self.db.add(letter)
            await self.db.flush()
            return letter
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def create_letter_recipient(
        self, tenant_id: uuid.UUID, letter_id: uuid.UUID, property_id: uuid.UUID
    ):
        try:
            recipient = LetterRecipient(
                letter_id=letter_id,
                property_id=property_id,
                tenant_id=tenant_id,
                is_read=False,
                read_at=None,
            )

            self.db.add(recipient)
            await self.db.commit()
            await self.db.refresh(recipient)
            return recipient

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_by_hash(self, property_id: uuid.UUID, file_hash: str):
        stmt = select(Letter).where(
            Letter.property_id == property_id,
            Letter.file_hash == file_hash,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def bulk_create_letter_recipient(
        self, tenant_ids: list[uuid.UUID], letter_id: uuid.UUID, property_id: uuid.UUID
    ):
        recipients = [
            LetterRecipient(
                letter_id=letter_id,
                tenant_id=tenant_id,
                property_id=property_id,
                is_read=False,
                read_at=None,
            )
            for tenant_id in tenant_ids
        ]

        self.db.add_all(recipients)
        return recipients

    async def update_is_read(
        self, letter_recipient_id: uuid.UUID, is_read: bool = True
    ):
        try:
            await self.db.execute(
                update(LetterRecipient)
                .where(LetterRecipient.id == letter_recipient_id)
                .values(is_read=is_read, read_at=datetime.utcnow())
            )
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def db_commit(self):
        try:
            await self.db.commit()

        except SQLAlchemyError:
            await self.db.rollback()
            raise
