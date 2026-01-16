import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from core.breaker import breaker
from core.cache import cache
from core.check_permission import CheckRolePermission
from core.event_publish import publish_event
from core.paginate import PaginatePage
from fastapi import HTTPException
from repos.lga_repos import LGARepo


class LGAService:
    def __init__(self, db):
        self.repo = LGARepo(db)
        self.paginate: PaginatePage = PaginatePage()
        self.permission: CheckRolePermission = CheckRolePermission()

    async def get_lga(self, lga_id: uuid.UUID):
        async def handler():
            cache_key = f"lga:{lga_id}"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            lga = await self.repo.get_one(lga_id)
            if not lga:
                raise HTTPException(status_code=404, detail="LGA not found")

            lga_dict = lga.to_dict()
            await cache.set_json(cache_key, lga_dict, ttl=300)
            return lga_dict

        return await breaker.call(handler)

    async def get_lga_by_name(self, name: str):
        async def handler():
            cache_key = f"lga_name:{name.lower()}"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            lga = await self.repo.get_by_name(name)
            if not lga:
                raise HTTPException(status_code=404, detail="LGA not found")

            lga_dict = lga.to_dict()
            await cache.set_json(cache_key, lga_dict, ttl=300)
            return lga_dict

        return await breaker.call(handler)

    async def get_all_lgas(self, page: int = 1, per_page: int = 20):
        async def handler():
            cache_key = "lgas:list"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            lgas = await self.repo.get_all()
            lga_dicts = [l.to_dict() for l in lgas]
            if not lga_dicts:
                return []
            paginated_lgas = self.paginate.paginate(lga_dicts, page, per_page)
            await cache.set_json(cache_key, paginated_lgas, ttl=300)
            return paginated_lgas

        return await breaker.call(handler)

    async def get_all_lgas_with_states(self, page: int = 1, per_page: int = 20):
        async def handler():
            cache_key = f"lgas:with_states:page:{page}:per:{per_page}"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            lgas = await self.repo.get_all_with_state()
            lga_dicts = [l.to_dict() for l in lgas]
            paginated_lgas = self.paginate.paginate(lga_dicts, page, per_page)
            await cache.set_json(cache_key, paginated_lgas, ttl=300)
            return paginated_lgas

        return await breaker.call(handler)

    async def create_lga(
        self,
        name: str,
        state_id: uuid.UUID,
    ):
        async def handler():
            existing = await self.repo.get_by_name(name)
            if existing:
                raise HTTPException(status_code=400, detail="LGA name already exists")

            lga = await self.repo.create(
                name=name,
                state_id=state_id,
            )
            lga_id = lga.id

            await cache.delete_cache_keys_async(
                f"lga:{lga_id}",
                f"lga_name:{lga.name.lower()}",
                "lgas:list",
                "lgas:with_states",
            )

            asyncio.create_task(
                publish_event(
                    "lga.created",
                    {
                        "lga_id": str(lga.id),
                        "name": lga.name,
                        "state_id": str(state_id),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                ),
            )

            return lga.as_dict(preload_state=lga.state)

        return await breaker.call(handler)

    async def update_lga(
        self, current_user, lga_id: uuid.UUID, new_name: Optional[str] = None
    ):
        async def handler():
            await self.permission.check_admin(current_user=current_user)
            lga = await self.repo.update_one(lga_id, new_name=new_name)

            await cache.delete_cache_keys_async(
                f"lga:{lga_id}",
                f"lga_name:{lga.name.lower()}",
                "lgas:list",
                "lgas:with_states",
            )

            asyncio.create_task(
                publish_event(
                    "lga.updated",
                    {
                        "lga_id": str(lga.id),
                        "name": lga.name,
                        "state_id": str(lga.state_id),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                ),
            )
            return lga.to_dict()

        return await breaker.call(handler)

    async def delete_lga(self, name: str, current_user):
        async def handler():
            await self.permission.check_admin(current_user=current_user)
            lga = await self.repo.delete_one(name=name)
            lga_id = lga.id

            await cache.delete_cache_keys_async(
                f"lga:{lga_id}",
                f"lga_name:{lga.name.lower()}",
                "lgas:list",
                "lgas:with_states",
            )

            asyncio.create_task(
                publish_event(
                    "lga.deleted",
                    {
                        "lga_id": str(lga.id),
                        "name": lga.name,
                        "state_id": str(lga.state_id),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                ),
            )
            return {"deleted": True, "id": str(lga.id), "name": lga.name}

        return await breaker.call(handler)
