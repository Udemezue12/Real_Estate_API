import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from geoalchemy2.shape import from_shape

from core.breaker import breaker
from core.cache import cache
from core.check_permission import CheckRolePermission
from core.event_publish import publish_event
from core.geoapify import geocode_address
from core.paginate import PaginatePage
from core.redis_idempotency import RedisIdempotency
from repos.lga_repos import LGARepo
from repos.state_repos import StateRepo
from states_lists.lga import LOCATIONS as locations


class LGAService:
    LOCK_KEY = "lgas:sync:v2"

    def __init__(self, db):
        self.repo = LGARepo(db)
        self.state_repo = StateRepo(db)
        self.paginate: PaginatePage = PaginatePage()
        self.permission: CheckRolePermission = CheckRolePermission()
        self.redis_idempotency = RedisIdempotency("lga-service-startup")

    async def get_lga(self, lga_id: uuid.UUID, current_user):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
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

    async def get_lga_by_name(self, name: str, current_user):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
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

    async def get_all_lgas(self, current_user, page: int = 1, per_page: int = 20):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
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

    async def get_all_lgas_with_states(
        self, current_user, page: int = 1, per_page: int = 20
    ):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
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
    ):
        # async def _sync():
        print("Starting LGA sync...")

        for state_name, payload in locations.items():
            state = await self.state_repo.get_name(state_name)

            if not state:
                print(f"Skipping LGAs for '{state_name}' (state not found)")
                continue

            state_id = state.id

            for lga_name in payload["lgas"]:
                point = await geocode_address(lga_name)
                geom = from_shape(point, srid=4326)

                lga, created = await self.repo.create_or_get(
                    name=lga_name,
                    state_id=state_id,
                    geom=geom,
                )

                if created:
                    await publish_event(
                        "lga.created",
                        {
                            "lga_id": str(lga.id),
                            "name": lga.name,
                            "state_id": str(state_id),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

        await cache.delete_cache_keys_async(
            "states:with_lgas",
            "lgas:list",
        )

        print("LGA sync completed")

    # await self.redis_idempotency.run_once(
    #     key=self.LOCK_KEY,
    #     coro=_sync,
    #     ttl=300,
    # )

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
                "states:with_lgaslgas:with_states",
            )

            (
                await publish_event(
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
                "states:with_lgaslgas:with_states",
            )

            (
                await publish_event(
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

    async def create(self, name: str, state_id: uuid.UUID, current_user):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
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

            
            await publish_event(
                    "lga.created",
                    {
                        "lga_id": str(lga.id),
                        "name": lga.name,
                        "state_id": str(state_id),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                ),
            

            return lga.as_dict(preload_state=lga.state)

        return await breaker.call(handler)
