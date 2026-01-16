import uuid
from datetime import datetime, timezone

from core.cache import cache
from core.event_publish import publish_event


class AsyncioProperty:
    async def _cache_delete(
        self,
        user_id: uuid.UUID,
        property_id: uuid.UUID,
        lga_id: uuid.UUID,
        state_id: uuid.UUID,
    ):
        try:
            await cache.delete_cache_keys_async(
                f"property:{user_id}{property_id}{state_id}",
                f"properties:{user_id}:{state_id}",
                f"properties:{user_id}:{lga_id}",
                f"property::{user_id}:{lga_id}:{property_id}",
            )
        except Exception:
            print("Cache delete skipped (redis unavailable)")

    async def create(self, prop, user_id: uuid.UUID, property_id: uuid.UUID):
        await self._cache_delete(
            user_id=user_id,
            property_id=property_id,
            lga_id=prop.lga_id,
            state_id=prop.state_id,
        )
        await publish_event(
            "property.created",
            {
                "property_id": str(prop.id),
                "address": prop.address,
                "property_owner": str(prop.owner),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def update(self, prop, user_id: uuid.UUID, property_id: uuid.UUID):
        await self._cache_delete(
            user_id=user_id,
            property_id=property_id,
            lga_id=prop.lga_id,
            state_id=prop.state_id,
        )
        await publish_event(
            "property.updated",
            {
                "property_id": str(prop.id),
                "address": prop.address,
                "property_owner": str(prop.owner),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def delete(self, prop, user_id: uuid.UUID, property_id: uuid.UUID):
        await self._cache_delete(
            user_id=user_id,
            property_id=property_id,
            lga_id=prop.lga_id,
            state_id=prop.state_id,
        )
        await publish_event(
            "property.updated",
            {
                "property_id": str(prop.id),
                "address": prop.address,
                "property_owner": str(prop.owner),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
