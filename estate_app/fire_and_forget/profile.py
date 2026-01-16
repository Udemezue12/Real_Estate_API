import uuid

from core.cache import cache
from core.cloudinary_setup import CloudinaryClient
from core.event_publish import publish_event
from fastapi import HTTPException
from tasks.get_nin_provider_tasks import GetNinProvider
from tasks.get_bvn_provider_tasks import GetBVNProvider


class AsyncioUserProfile:
    def __init__(self):
        self.select_nin_provider: GetNinProvider = GetNinProvider()
        self.select_bvn_provider: GetBVNProvider = GetBVNProvider()
        self.cloudinary: CloudinaryClient = CloudinaryClient()

    async def profile_create(self, profile, data, user_id: uuid.UUID):
        try:
            self.select_nin_provider.get_provider(
                data=data, profile_id=profile.id
            )
            self.select_bvn_provider.get_provider(
                data=data, profile_id=profile.id
            )

            await cache.delete_cache_keys_async(
                f"user_id:{user_id}:profile:{profile.id}"
            )

            await publish_event(
                "profile.created",
                {
                    "profile_id": str(profile.id),
                    "user_id": str(user_id),
                    "url": profile.profile_pic_path,
                },
            )

        except Exception as e:
            print(f"Post profile creation task failed", {e})
            raise HTTPException(403, "Post Profile Creation Failed")

    async def profile_update(
        self, public_id: str, profile, current_user, resource_type: str
    ):
        await self.cloudinary.safe_delete_cloudinary(
            public_id=public_id, resource_type=resource_type
        )
        await cache.delete_cache_keys_async(
            f"user_id:{current_user.id}:profile:{profile.id}"
        )
        await publish_event(
            "profile.updated",
            {
                "profile_id": str(profile.id),
                "user_id": str(current_user.id),
                "url": profile.profile_pic_path,
            },
        )

    async def profile_delete(
        self,
        *,
        public_id: str,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        resource_type: str,
    ):
        try:
            await self.cloudinary.safe_delete_cloudinary(public_id, resource_type)

            await cache.delete_cache_keys_async(
                f"user_id:{user_id}:profile:{profile_id}"
            )

        except Exception as e:
            raise HTTPException(403, "Error")
