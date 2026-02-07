import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from core.breaker import breaker
from core.cache import cache
from core.check_permission import CheckRolePermission
from core.event_publish import publish_event
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from core.redis_idempotency import RedisIdempotency
from repos.lga_repos import LGARepo
from repos.property_repo import PropertyRepo
from schemas.schema import PropertyOut


class PropertyService:
    LOCK_KEY = "property-service-lock-v2"

    def __init__(self, db):
        self.repo: PropertyRepo = PropertyRepo(db)
        self.paginate: PaginatePage = PaginatePage()
        self.lga_repo: LGARepo = LGARepo(db)
        self.permission: CheckRolePermission = CheckRolePermission()
        self.idempotency: RedisIdempotency = RedisIdempotency(
            namespace="property-service"
        )
        self.mapper: ORMMapper = ORMMapper()

    async def check_owner(self, property_id: uuid.UUID, user_id: uuid.UUID):
        prop = await self.repo.get_by_id(property_id)
        if not prop:
            raise HTTPException(404, "Property not found")

        if prop.owner_id != user_id:
            raise HTTPException(
                403, "You are not allowed"
            )
        return prop

    async def create_property(self, data, current_user):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            existing_title = await self.repo.get_by_title(title=data.title)
            existing_address = await self.repo.get_by_address(address=data.address)
            existing_description = await self.repo.get_by_description(
                description=data.description
            )
            if existing_address:
                raise HTTPException(
                    status_code=400, detail="Property already exists in this address"
                )
            if existing_title:
                raise HTTPException(
                    status_code=400, detail="This Title has already been Taken"
                )
            if existing_description:
                raise HTTPException(
                    status_code=400, detail="This Description has already been Taken"
                )
            state_check = data.state_id
            lga_check = data.lga_id
            await self.lga_repo.validate_state_lga_match(
                state_id=state_check, lga_id=lga_check
            )
            user_id = current_user.id
            props = await self.repo.create_first(
                owner_id=user_id,
                state_id=state_check,
                lga_id=lga_check,
                title=data.title,
                description=data.description,
                address=data.address,
                rooms=data.rooms,
                bathrooms=data.bathrooms,
                toilets=data.toilets,
                default_rent_amount=Decimal(str(data.default_rent_amount)),
                default_rent_cycle=data.default_rent_cycle,
                house_type=data.house_type,
                property_type=data.property_type,
                square_meters=data.square_meters,
                is_owner=data.is_owner,
                is_manager=data.is_manager,
                managed_by_id=data.managed_by_id,
            )
            prop = await self.repo.get_property_with_relations(props.id)

            await self.cache_delete(
                user_id=user_id,
                property_id=props.id,
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

            return self.mapper.one(prop, PropertyOut)

        return await breaker.call(handler)

    async def update_property(self, property_id: uuid.UUID, current_user, data):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)

            await self.check_owner(property_id=property_id, user_id=user_id)
            update_data = data.model_dump(exclude_unset=True)

            if not update_data:
                raise HTTPException(
                    status_code=400,
                    detail="No fields provided for update.",
                )

            new_prop = await self.repo.update(
                user_id=user_id,
                property_id=property_id,
                **update_data,
            )

            prop = await self.repo.get_property_with_relations(new_prop.id)

            await self.cache_delete(
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

            return self.mapper.one(prop, PropertyOut)

        return await breaker.call(handler)

    async def delete_property(self, current_user, property_id: uuid.UUID):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            prop = await self.check_owner(property_id=property_id, user_id=user_id)

            await self.repo.delete_property(user_id=user_id, property_id=property_id)

            await self.cache_delete(
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

            return JSONResponse(
                {
                    "message": "Delete successful",
                }
            )

        return await breaker.call(handler)

    async def get_single_property_by_user(
        self, property_id: uuid.UUID, current_user
    ) -> PropertyOut:
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            await self.check_owner(property_id=property_id, user_id=user_id)
            cache_key = f"property:{user_id}:{property_id}"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.one(cached, PropertyOut)
            props = await self.repo.get_single_property_by_user(
                property_id=property_id, user_id=user_id
            )
            if not props or props.owner_id != user_id:
                raise HTTPException(404, "Property not found")
            prop_dict = self.mapper.one(props, PropertyOut)

            await cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(prop_dict=prop_dict),
                ttl=300,
            )
            return prop_dict

        return await breaker.call(handler)

    async def get_property_by_state_user(
        self, property_id: uuid.UUID, state_id: uuid.UUID, current_user
    ) -> PropertyOut:
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            await self.check_owner(property_id=property_id, user_id=user_id)
            cache_key = f"property:{user_id}:{property_id}:{state_id}"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.one(cached, PropertyOut)
            props = await self.repo.get_property_by_state_user(
                state_id, property_id, user_id
            )
            if not props or props.owner_id != user_id:
                raise HTTPException(404, "Property not found")
            prop_dict = self.mapper.one(props, PropertyOut)

            await cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(prop_dict=prop_dict),
                ttl=300,
            )
            return prop_dict

        return await breaker.call(handler)

    async def get_properties_by_state_user(
        self, state_id: uuid.UUID, current_user, page: int = 1, per_page: int = 20
    ) -> List[PropertyOut]:
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"properties:{user_id}:{state_id}:page:{page}:per:{per_page}"
            cached = await cache.get_json(cache_key)
            print(f"Cached:::{cached}")
            if cached:
                return self.mapper.many(items=cached, schema=PropertyOut)
            props = await self.repo.get_properties_by_state_user(
                state_id=state_id, user_id=user_id
            )
            props_dicts = self.mapper.many(items=props, schema=PropertyOut)
            paginated_props = self.paginate.paginate(props_dicts, page, per_page)
            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_props=paginated_props),
                ttl=300,
            )
            return paginated_props

        return await breaker.call(handler)

    async def get_properties_by_user(
        self, current_user, page: int = 1, per_page: int = 20
    ) -> List[PropertyOut]:
        async def handler():
            user_id=current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"properties:{user_id}:all:page:{page}:per:{per_page}"
            cached = await cache.get_json(cache_key)
            print(f"Cached:::{cached}")
            if cached:
                return self.mapper.many(items=cached, schema=PropertyOut)
            props = await self.repo.get_all_by_user(user_id=user_id)
            props_dicts = self.mapper.many(items=props, schema=PropertyOut)
            paginated_props = self.paginate.paginate(props_dicts, page, per_page)
            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_props=paginated_props),
                ttl=300,
            )
            return paginated_props

        return await breaker.call(handler)

    async def get_properties_by_lga_user(
        self,
        lga_id: uuid.UUID,
        current_user,
        page: int = 1,
        per_page: int = 20,
    ) -> List[PropertyOut]:
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"properties:{user_id}:{lga_id}:page:{page}:per:{per_page}"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.many(items=cached, schema=PropertyOut)
            props = await self.repo.get_properties_by_lga_user(lga_id, user_id)

            props_dicts = self.mapper.many(items=props, schema=PropertyOut)
            paginated_props = self.paginate.paginate(props_dicts, page, per_page)
            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_props=paginated_props),
                ttl=300,
            )
            return paginated_props

        return await breaker.call(handler)

    async def get_one_property(
        self,
        lga_id: uuid.UUID,
        property_id: uuid.UUID,
        current_user,
    ) -> Optional[PropertyOut]:
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            await self.check_owner(property_id=property_id, user_id=user_id)
            cache_key = f"property::{user_id}:{lga_id}:{property_id}"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.one(item=cached, schema=PropertyOut)
            prop = await self.repo.get_property_by_lga_user(
                lga_id, property_id, user_id
            )
            if not prop:
                raise HTTPException(status_code=404, detail="Property not found")
            prop_dict = self.mapper.one(prop, PropertyOut)

            await cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(prop_dict=prop_dict),
                ttl=300,
            )
            return prop_dict

        return await breaker.call(handler)

    async def mark_as_verified(self, property_id: uuid.UUID, current_user):
        async def _start():
            # await self.permission.check_admin(current_user=current_user)
            property = await self.repo.get_it_by_id(property_id)
            if not property:
                raise HTTPException(404, "Not Found")
            if property.is_verified:
                raise HTTPException(403, "This property has already been verified")
            await self.repo.mark_property_verified(
                property_id=property_id, is_verified=True
            )
            await self.cache_delete(
                user_id=property.owner_id,
                property_id=property_id,
                lga_id=property.lga_id,
                state_id=property.state_id,
            )
            return {"message": "Verified Successfully"}

        return await self.idempotency.run_once(key=self.LOCK_KEY, coro=_start, ttl=120)

    async def cache_delete(
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
                f"property::{user_id}:{lga_id}:{property_id}properties:{user_id}:all",
                f"property:{user_id}:{property_id}",
            )
        except Exception:
            print("Cache delete skipped (redis unavailable)")
