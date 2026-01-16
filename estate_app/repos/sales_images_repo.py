import uuid
from datetime import datetime

from fastapi import HTTPException
from models.models import SaleListingImage
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError


class SaleListingImageRepo:
    def __init__(self, db):
        self.db = db

    async def get_by_hash(self, listing_id: uuid.UUID, image_hash: str):
        stmt = select(SaleListingImage).where(
            SaleListingImage.listing_id == listing_id,
            SaleListingImage.image_hash == image_hash,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_listing(self, listing_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(SaleListingImage.id)).where(
                SaleListingImage.listing_id == listing_id
            )
        )
        return result.scalar_one()

    async def count_user_uploads_between(
        self,
        user_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> SaleListingImage:
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)

        if end.tzinfo is not None:
            end = end.replace(tzinfo=None)
        stmt = (
            select(func.count(SaleListingImage.id))
            .where(SaleListingImage.created_by_id== user_id)
            .where(SaleListingImage.uploaded_at >= start)
            .where(SaleListingImage.uploaded_at < end)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def create(
        self,
        listing_id: uuid.UUID,
        sale_image_creator: uuid.UUID,
        image_url: str,
        image_hash: str,
        public_id: str,
        created_by_id: uuid.UUID,
    ) -> SaleListingImage:
        image = SaleListingImage(
            image_path=image_url,
            image_hash=image_hash,
            public_id=public_id,
            listing_id=listing_id,
            created_by_id=created_by_id,
            sale_image_creator=sale_image_creator
        )
        self.db.add(image)
        try:
            await self.db.commit()
            await self.db.refresh(image)
            return image
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_one(self, image_id: uuid.UUID) -> SaleListingImage | None:
        result = await self.db.execute(
            select(SaleListingImage).where(SaleListingImage.id == image_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, listing_id: uuid.UUID) -> list[SaleListingImage]:
        result = await self.db.execute(
            select(SaleListingImage).where(SaleListingImage.listing_id == listing_id)
        )
        return result.scalars().all()

    async def update_one(
        self,
        image_id: uuid.UUID,
        *,
        new_url: str | None = None,
        new_hash: str | None = None,
        new_public_id: str | None = None,
        new_listing_id: uuid.UUID | None = None,
    ) -> SaleListingImage:
        values = {}
        if new_url:
            values["image_path"] = new_url
        if new_hash:
            values["image_hash"] = new_hash
        if new_public_id:
            values["public_id"] = new_public_id
        if new_listing_id:
            values["listing_id"] = new_listing_id
        stmt = (
            update(SaleListingImage)
            .where(SaleListingImage.id == image_id)
            .values(**values)
            .returning(SaleListingImage)
        )

        result = await self.db.execute(stmt)
        updated = result.scalar_one_or_none()

        if not updated:
            raise HTTPException(status_code=404, detail="Image not found")

        await self.db.commit()
        return updated

    async def delete_one(self, image_id: uuid.UUID):
        stmt = (
            delete(SaleListingImage)
            .where(SaleListingImage.id == image_id)
            .returning(SaleListingImage)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        deleted = result.scalar_one_or_none()
        if not deleted:
            raise HTTPException(status_code=404, detail="Image not found")
        return deleted

    async def delete_all_for_listing(self, listing_id: uuid.UUID):
        stmt = delete(SaleListingImage).where(SaleListingImage.listing_id == listing_id)
        await self.db.execute(stmt)
        await self.db.commit()
