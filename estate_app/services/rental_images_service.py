import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from core.breaker import breaker
from core.cache import cache
from core.check_permission import CheckRolePermission
from core.cloudinary_setup import CloudinaryClient
from core.delete_token import DeleteTokenGenerator
from core.event_publish import publish_event
from core.file_hash import ComputeFileHash
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from core.redis_idempotency import RedisIdempotency
from repos.rental_images_repo import RentalListingImageRepo
from schemas.schema import BaseImageOut

MAX_DAILY_UPLOADS = 4


class RentalListingImageService:
    CREATE_LOCK_KEY = "create-rental-images:sync:v2"
    UPDATE_LOCK_KEY = "update-rental-images:sync:v2"
    DELETE_LOCK_KEY = "delete-rental-images:sync:v2"

    def __init__(
        self,
        db,
    ):
        self.repo: RentalListingImageRepo = RentalListingImageRepo(db)
        self.cloudinary: CloudinaryClient = CloudinaryClient()
        self.paginate: PaginatePage = PaginatePage()
        self.token_delete: DeleteTokenGenerator = DeleteTokenGenerator()
        self.compute: ComputeFileHash = ComputeFileHash()
        self.mapper: ORMMapper = ORMMapper()
        self.permission: CheckRolePermission = CheckRolePermission()
        self.redis_idempotency = RedisIdempotency("rental-images-service-startup")

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
        self, current_user, listing_id: uuid.UUID, page: int = 1, per_page: int = 20
    ) -> list[BaseImageOut]:
        await self.permission.check_authenticated(current_user=current_user)
        cache_key = f"sale_listing:{listing_id}:images{page}:{per_page}"
        cached = await cache.get_json(cache_key)
        if cached:
            return self.mapper.many(items=cached, schema=BaseImageOut)
        images = await self.repo.get_all(listing_id)
        images_out = self.mapper.many(items=images, schema=BaseImageOut)
        paginated_images = self.paginate.paginate(images_out, page, per_page)
        await cache.set_json(
            cache_key,
            self.paginate.get_list_json_dumps(paginated_images),
            ttl=300,
        )
        return paginated_images

    async def upload_image(
        self,
        rent_listing_id: uuid.UUID,
        image_url: str,
        current_user,
        public_id: str,
    ):
        async def _handler():
            await self.permission.check_authenticated(current_user=current_user)
            count = await self.repo.count_for_listing(listing_id=rent_listing_id)

            if count >= 3:
                raise HTTPException(
                    status_code=400, detail="Maximum of 3 images allowed per listing."
                )
            image_hash = await self.compute.compute_file_hash(image_url)
            existing = await self.repo.get_by_hash(
                listing_id=rent_listing_id, image_hash=image_hash
            )
            if existing:
                raise HTTPException(400, "This image has already been uploaded")

            image = await self.repo.create(
                listing_id=rent_listing_id,
                image_url=image_url,
                image_hash=image_hash,
                public_id=public_id,
                created_by_id=current_user.id,
                rental_image_creator=current_user.id,
            )
            await cache.delete_cache_keys_async(
                f"rental_listing:{rent_listing_id}:images"
            )

            await publish_event(
                "rental_listing.image.created",
                {
                    "listing_id": str(rent_listing_id),
                    "image_id": str(image.id),
                    "url": image.image_path,
                },
            )

            return {"id": str(image.id), "url": image.image_path}

        return await self.redis_idempotency.run_once(
            key=self.CREATE_LOCK_KEY,
            coro=_handler,
            ttl=300,
        )

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
            await self.repo.db_rollback()
            await self._safe_delete_cloudinary(public_id=public_id)
            raise HTTPException(500, "Failed to update image")

    async def update_image(
        self,
        image_id: uuid.UUID,
        secure_url: str,
        public_id: str,
        current_user,
    ):
        async def _sync():
            old_image = await self.repo.get_one(image_id)
            if not old_image:
                raise HTTPException(status_code=404, detail="Image not found")
            if old_image.created_by_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="You cannot update an image you didn't create",
                )
            count = await self.repo.count_for_listing(old_image.listing_id)
            if count > 5:
                raise HTTPException(
                    status_code=400,
                    detail="This listing already exceeds the maximum of 5 images.",
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
                f"rental_listing:{old_image.listing_id}:images"
            )

            return {"id": str(updated.id), "url": updated.image_path}

        return await self.redis_idempotency.run_once(
            key=self.UPDATE_LOCK_KEY,
            coro=_sync,
            ttl=300,
        )

    async def delete_image(
        self, image_id: uuid.UUID, current_user, resource_type: str = "images"
    ):
        async def _sync():
            await self.permission.check_authenticated(current_user=current_user)
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

            await self.cloudinary.delete_image(
                public_id=image.public_id, resource_type=resource_type
            )
            await self.repo.delete_one(image_id)
            await cache.delete_cache_keys_async(
                f"rental`_listing:{image.listing_id}:images"
            )
            return {"deleted": True, "id": str(image.id)}

        return await self.redis_idempotency.run_once(
            key=self.DELETE_LOCK_KEY,
            coro=_sync,
            ttl=300,
        )

    async def _safe_delete_cloudinary(
        self, public_id: str, resource_type: str = "images"
    ):
        try:
            await self.cloudinary.delete_image(
                public_id=public_id, resource_type=resource_type
            )
        except Exception:
            pass
