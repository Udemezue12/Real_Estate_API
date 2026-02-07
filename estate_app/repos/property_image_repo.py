import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError

from models.models import PropertyImage


class PropertyImageRepo:
    def __init__(self, db):
        self.db = db

    async def get_by_hash(self, property_id: uuid.UUID, image_hash: str):
        stmt = select(PropertyImage).where(
            PropertyImage.property_id == property_id,
            PropertyImage.image_hash == image_hash,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_listing(self, property_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(PropertyImage.id)).where(
                PropertyImage.property_id == property_id
            )
        )
        return result.scalar_one()

    async def count_user_uploads_between(
        self,
        user_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> PropertyImage:
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)

        if end.tzinfo is not None:
            end = end.replace(tzinfo=None)
        stmt = (
            select(func.count(PropertyImage.id))
            .where(PropertyImage.property_by_id == user_id)
            .where(PropertyImage.uploaded_at >= start)
            .where(PropertyImage.uploaded_at < end)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def create(
        self,
        property_id: uuid.UUID,
        property_image_creator: uuid.UUID,
        image_url: str,
        image_hash: str,
        public_id: str,
        property_by_id: uuid.UUID,
    ) -> PropertyImage:
        image = PropertyImage(
            image_path=image_url,
            image_hash=image_hash,
            public_id=public_id,
            property_id=property_id,
            property_by_id=property_by_id,
            property_image_creator=property_image_creator,
        )
        self.db.add(image)
        try:
            await self.db.commit()
            await self.db.refresh(image)
            return image
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_one(self, image_id: uuid.UUID) -> PropertyImage | None:
        result = await self.db.execute(
            select(PropertyImage).where(PropertyImage.id == image_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, property_id: uuid.UUID, page: int = 1, per_page: int = 20
    ) -> list[PropertyImage]:
        result = await self.db.execute(
            select(PropertyImage)
            .where(PropertyImage.property_id == property_id)
            .order_by(PropertyImage.id)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return result.scalars().all()

    async def update_one(
        self,
        image_id: uuid.UUID,
        *,
        new_url: str | None = None,
        new_hash: str | None = None,
        new_public_id: str | None = None,
        new_property_id: uuid.UUID | None = None,
    ) -> PropertyImage:
        values = {}
        if new_url:
            values["image_path"] = new_url
        if new_hash:
            values["image_hash"] = new_hash
        if new_public_id:
            values["public_id"] = new_public_id
        if new_property_id:
            values["property_id"] = new_property_id
        stmt = (
            update(PropertyImage)
            .where(PropertyImage.id == image_id)
            .values(**values)
            .returning(PropertyImage)
        )

        result = await self.db.execute(stmt)
        updated = result.scalar_one_or_none()

        if not updated:
            raise HTTPException(status_code=404, detail="Image not found")

        await self.db.commit()
        return updated

    async def delete_one(self, image_id: uuid.UUID):
        stmt = (
            delete(PropertyImage)
            .where(PropertyImage.id == image_id)
            .returning(PropertyImage)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        deleted = result.scalar_one_or_none()
        if not deleted:
            raise HTTPException(status_code=404, detail="Image not found")
        return deleted

    async def delete_all_for_listing(self, property_id: uuid.UUID):
        stmt = delete(PropertyImage).where(PropertyImage.property_id == property_id)
        await self.db.execute(stmt)
        await self.db.commit()
    async def db_rollback(self):
        await self.db.rollback()
