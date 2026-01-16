import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from core.breaker import breaker
from core.cache import cache
from core.cloudinary_setup import CloudinaryClient
from core.delete_token import DeleteTokenGenerator
from core.event_publish import publish_event
from core.file_hash import ComputeFileHash
from core.paginate import PaginatePage
from fastapi import HTTPException
from repos.sales_images_repo import SaleListingImageRepo

MAX_DAILY_UPLOADS = 4


class SaleListingImageService:
    def __init__(
        self,
        db,
    ):
        self.repo: SaleListingImageRepo = SaleListingImageRepo(db)
        self.cloudinary: CloudinaryClient = CloudinaryClient()
        self.paginate: PaginatePage = PaginatePage()
        self.token_delete: DeleteTokenGenerator = DeleteTokenGenerator()
        self.compute: ComputeFileHash = ComputeFileHash()

    async def enforce_daily_quota(self, user_id: uuid.UUID):
        today_start = (
            datetime.now(timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .replace(tzinfo=None)
        )
        tomorrow = today_start + timedelta(days=1)

        count = await self.repo.count_user_uploads_between(
            user_id=user_id,
            start=today_start,
            end=tomorrow,
        )

        if count >= MAX_DAILY_UPLOADS:
            raise HTTPException(status_code=429, detail="Daily upload limit reached")

    async def get_all_images(
        self, listing_id: uuid.UUID, page: int = 1, per_page: int = 20
    ):
        cache_key = f"sale_listing:{listing_id}:images"
        cached = await cache.get_json(cache_key)
        if cached:
            return cached
        images = await self.repo.get_all(listing_id)
        image_dicts = [{"id": str(img.id), "url": img.image_path} for img in images]
        paginated_images = self.paginate.paginate(image_dicts, page, per_page)
        await cache.set_json(cache_key, paginated_images, ttl=300)
        return paginated_images

    async def upload_image(
        self,
        listing_id: uuid.UUID,
        image_url: str,
        current_user,
        public_id: str,
    ):
        async def handler():
            await self.enforce_daily_quota(user_id=current_user.id)
            count = await self.repo.count_for_listing(listing_id)

            if count >= 5:
                raise HTTPException(
                    status_code=400, detail="Maximum of 5 images allowed per listing."
                )
            image_hash = await self.compute.compute_file_hash(image_url)
            print(f"Image_hash::{image_hash}")
            existing = await self.repo.get_by_hash(listing_id, image_hash)
            if existing:
                raise HTTPException(400, "This image has already been uploaded")

            image = await self.repo.create(
                listing_id=listing_id,
                image_url=image_url,
                image_hash=image_hash,
                public_id=public_id,
                created_by_id=current_user.id,
                sale_image_creator=current_user.id,
            )
            await cache.delete_cache_keys_async(f"sale_listing:{listing_id}:images")

            asyncio.create_task(
                publish_event(
                    "sale_listing.image.created",
                    {
                        "listing_id": str(listing_id),
                        "image_id": str(image.id),
                        "url": image.image_path,
                    },
                )
            )
            return {"id": str(image.id), "url": image.image_path}

        return await breaker.call(handler)

    async def _update_image_record(
        self,
        *,
        image_id: uuid.UUID,
        secure_url: str,
        new_hash: str,
        public_id: str,
        
    ):
        try:
            return await self.repo.update_one(
                image_id=image_id,
                new_url=secure_url,
                new_hash=new_hash,
                new_public_id=public_id,
            )
        except Exception:
            await self.repo.db.rollback()
            await self._safe_delete_cloudinary(public_id=public_id)
            raise HTTPException(500, "Failed to update image")

    async def update_image(
        self,
        image_id: uuid.UUID,
        secure_url: str,
        public_id: str,
        current_user,
       
    ):
        async def handler():
            old_image = await self.repo.get_one(image_id)
            if not old_image:
                raise HTTPException(status_code=404, detail="Image not found")
            if old_image.created_by_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="You cannot update an image you didn't create",
                )

            new_hash = await self.compute.compute_file_hash(secure_url)
            existing = await self.repo.get_by_hash(old_image.listing_id, new_hash)
            if existing and existing.id != image_id:
                raise HTTPException(
                    status_code=400,
                    detail="Another image with this content already exists",
                )

            updated = await self._update_image_record(
                image_id=image_id,
                secure_url=secure_url,
                new_hash=new_hash,
                public_id=public_id,
                
            )
            await self._safe_delete_cloudinary(public_id=old_image.public_id)
            await cache.delete_cache_keys_async(
                f"sale_listing:{old_image.listing_id}:images"
            )

            return {"id": str(updated.id), "url": updated.image_path}

        return await breaker.call(handler)

    async def delete_image(self, image_id: uuid.UUID, current_user, resource_type:str="images"):
        async def handler():
            image = await self.repo.get_one(image_id)
            if not image:
                raise HTTPException(status_code=404, detail="Image not found")
            if image.created_by_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="You cannot delete an image you didn't create",
                )
            token = await self.token_delete.generate_token(image_id=str(image.id))

            validated_token = await self.token_delete.validate_token(
                image_id=str(image.id), token=token
            )

            if not validated_token:
                raise HTTPException(403, detail="Invalid delete token")

            await self.repo.delete_one(image_id)
            await cache.delete_cache_keys_async(
                f"sale_listing:{image.listing_id}:images"
            )
            await self.cloudinary.delete_image(public_id=image.public_id, resource_type=resource_type)
            return {"deleted": True, "id": str(image.id)}

        return await breaker.call(handler)

    async def _safe_delete_cloudinary(self, public_id: str, resource_type:str="images"):
        try:
            await self.cloudinary.delete_image(public_id, resource_type=resource_type)
        except Exception:
            pass
