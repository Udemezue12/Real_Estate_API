import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException
from geoalchemy2.shape import from_shape

from core.breaker import breaker
from core.cache import cache
from core.check_permission import CheckRolePermission
from core.event_publish import publish_event
from core.geoapify import geocode_address
from core.paginate import PaginatePage
from core.redis_idempotency import RedisIdempotency
from models.shape import convert_location
from repos.state_repos import StateRepo
from schemas.schema import LgaSchema, StateSchema
from states_lists.states import STATES


class StateService:
    LOCK_KEY = "states:sync:v12"

    def __init__(self, db):
        self.repo: StateRepo = StateRepo(db)
        self.paginate: PaginatePage = PaginatePage()
        self.permission: CheckRolePermission = CheckRolePermission()
        self.idempotency = RedisIdempotency(namespace="states-service-startup")

    async def get_states(self, page: int = 1, per_page: int = 20) -> List[dict]:
        async def handler():
            cache_key = "states:list"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
            states = await self.repo.get_all()

            state_dicts = [
                StateSchema(
                    id=s.id,
                    name=s.name,
                    location=convert_location(s.location),
                    lgas=[
                        LgaSchema(
                            id=l.id, name=l.name, location=convert_location(l.location)
                        )
                        for l in s.lgas
                    ],
                ).model_dump(mode="json")
                for s in states
            ]
            if not state_dicts:
                return []
            paginated_states = self.paginate.paginate(state_dicts, page, per_page)
            await cache.set_json(cache_key, paginated_states, ttl=300)
            return paginated_states

        return await breaker.call(handler)

    async def get_state_with_lga(
        self, state_name: str, page: int = 1, per_page: int = 20
    ):
        async def handler():
            cache_key = f"state:{state_name}"

            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            state = await self.repo.get_one(name=state_name)
            if not state:
                raise HTTPException(status_code=404, detail="State not found")
            paginated_state = self.paginate.paginate(state, page, per_page)

            await cache.set_json(cache_key, paginated_state, ttl=300)
            return paginated_state

        return await breaker.call(handler)

    async def get_all_states_with_lgas(self, page: int = 1, per_page: int = 20):
        async def handler():
            cache_key = "states:with_lgas"

            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            states = await self.repo.get_all_with_lgas()
            paginated_states = self.paginate.paginate(states, page, per_page)
            await cache.set_json(cache_key, paginated_states, ttl=300)
            return paginated_states

        return await breaker.call(handler)

    async def get_state(self, page: int = 1, per_page: int = 20):
        async def handler():
            cache_key = "state_name:single_state"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
            states = await self.repo.get_all_states()
            state_dicts = [s.as_dict() for s in states]
            paginated_states = self.paginate.paginate(state_dicts, page, per_page)
            await cache.set_json(cache_key, paginated_states, ttl=300)
            return paginated_states

        return await breaker.call(handler)

    async def create_state(
        self,
    ):
        # async def _sync():
            print("Starting state sync...")

            for item in STATES:
                raw_name = item["name"].strip()
                point = await geocode_address(raw_name)
                geom = from_shape(point, srid=4326)

                state, created = await self.repo.create_or_get(name=raw_name, geom=geom)
                await self.repo.db_commit()

                if created:
                    await publish_event(
                        "state.created",
                        {
                            "state_id": str(state.id),
                            "name": state.name,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

            await cache.delete_cache_keys_async(
                "states:list",
                "states:with_lgas",
            )

            print("State sync completed")

        # await self.idempotency.run_once(
        #     key=self.LOCK_KEY,
        #     coro=_sync,
        #     ttl=120,
        # )

    async def update_state(
        self, current_user, state_id: uuid.UUID, new_name: str | None = None
    ):
        async def handler():
            await self.permission.check_admin(current_user=current_user)
            state = await self.repo.update_one(
                state_id=state_id,
                new_name=new_name,
            )
            state_name = state.name

            (
                await publish_event(
                    "state.updated",
                    {
                        "state_id": str(state.id),
                        "name": str(state_name),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                ),
            )

            await cache.delete_cache_keys_async(
                f"state:{state_name}",
                "state_name:single_state",
                "states:list",
                "states:with_lgas",
            )
            return state.as_dict()

        return await breaker.call(handler)

    async def delete_state(
        self,
        current_user,
        name: str,
    ):
        async def handler():
            await self.permission.check_admin(current_user=current_user)
            state = await self.repo.get_name(name)
            if not state:
                raise HTTPException(status_code=404, detail="State not found")

            deleted = await self.repo.delete_one(name)
            state_name = deleted.name

            await cache.delete_cache_keys_async(
                f"state:{state_name}",
                "state_name:single_state",
                "states:list",
                "states:with_lgas",
            )
            (
                await publish_event(
                    "state.deleted",
                    {
                        "state_id": deleted.id,
                        "name": deleted.name,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                ),
            )

            return {"deleted": True, "id": state["id"], "name": state["name"]}

        return await breaker.call(handler)
