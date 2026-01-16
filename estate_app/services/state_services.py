import asyncio
from datetime import datetime, timezone
from typing import List
import uuid
from schemas.schema import LgaSchema, StateSchema
from core.breaker import breaker
from core.check_permission import CheckRolePermission
from core.paginate import PaginatePage
from core.cache import cache
from core.event_publish import publish_event
from fastapi import HTTPException
from repos.state_repos import StateRepo
from models.shape import convert_location


class StateService:
    def __init__(self, db):
        self.repo: StateRepo = StateRepo(db)
        self.paginate: PaginatePage = PaginatePage()
        self.permission: CheckRolePermission = CheckRolePermission()

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
        name: str,
    ):
        async def handler():
            if await self.repo.get_name(name=name):
                raise HTTPException(status_code=400, detail="Name already taken")

            state = await self.repo.create(
                name=name,
            )
            state_name = state.name

            asyncio.create_task(
                publish_event(
                    "state.created",
                    {
                        "state_id": str(state.id),
                        "name": state_name,
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

            asyncio.create_task(
                publish_event(
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
            asyncio.create_task(
                publish_event(
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
