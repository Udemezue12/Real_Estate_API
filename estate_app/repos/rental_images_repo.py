import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError

from models.models import RentalListingImage


class RentalListingImageRepo:
    def __init__(self, db):
        self.db = db

    async def get_by_hash(self, listing_id: uuid.UUID, image_hash: str):
        stmt = select(RentalListingImage).where(
            RentalListingImage.listing_id == listing_id,
            RentalListingImage.image_hash == image_hash,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_listing(self, listing_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(RentalListingImage.id)).where(
                RentalListingImage.listing_id == listing_id
            )
        )
        return result.scalar_one()

    async def count_user_uploads_between(
        self,
        user_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> RentalListingImage:
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)

        if end.tzinfo is not None:
            end = end.replace(tzinfo=None)
        stmt = (
            select(func.count(RentalListingImage.id))
            .where(RentalListingImage.created_by_id == user_id)
            .where(RentalListingImage.uploaded_at >= start)
            .where(RentalListingImage.uploaded_at < end)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def create(
        self,
        listing_id: uuid.UUID,
        rental_image_creator: uuid.UUID,
        image_url: str,
        image_hash: str,
        public_id: str,
        created_by_id: uuid.UUID,
    ) -> RentalListingImage:
        image = RentalListingImage(
            image_path=image_url,
            image_hash=image_hash,
            public_id=public_id,
            listing_id=listing_id,
            created_by_id=created_by_id,
            rental_image_creator=rental_image_creator,
        )
        self.db.add(image)
        try:
            await self.db.commit()
            await self.db.refresh(image)
            return image
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_one(self, image_id: uuid.UUID) -> RentalListingImage | None:
        result = await self.db.execute(
            select(RentalListingImage).where(RentalListingImage.id == image_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, listing_id: uuid.UUID, page: int = 1, per_page: int = 20
    ) -> list[RentalListingImage]:
        result = await self.db.execute(
            select(RentalListingImage)
            .where(RentalListingImage.listing_id == listing_id)
            .order_by(RentalListingImage.id)
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
        new_listing_id: uuid.UUID | None = None,
    ) -> RentalListingImage:
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
            update(RentalListingImage)
            .where(RentalListingImage.id == image_id)
            .values(**values)
            .returning(RentalListingImage)
        )

        result = await self.db.execute(stmt)
        updated = result.scalar_one_or_none()

        if not updated:
            raise HTTPException(status_code=404, detail="Image not found")

        await self.db.commit()
        return updated

    async def delete_one(self, image_id: uuid.UUID):
        stmt = (
            delete(RentalListingImage)
            .where(RentalListingImage.id == image_id)
            .returning(RentalListingImage)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        deleted = result.scalar_one_or_none()
        if not deleted:
            raise HTTPException(status_code=404, detail="Image not found")
        return deleted

    async def delete_all_for_listing(self, listing_id: uuid.UUID):
        stmt = delete(RentalListingImage).where(
            RentalListingImage.listing_id == listing_id
        )
        await self.db.execute(stmt)
        await self.db.commit()
    async def db_rollback(self):
        await self.db.rollback()
