import asyncio
import uuid
from typing import List, Optional

from core.breaker import breaker
from core.cache import cache
from core.check_permission import CheckRolePermission
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fire_and_forget.property import AsyncioProperty
from repos.lga_repos import LGARepo
from repos.property_repo import PropertyRepo
from schemas.schema import PropertyOut


class PropertyService:
    def __init__(self, db):
        self.repo: PropertyRepo = PropertyRepo(db)
        self.paginate: PaginatePage = PaginatePage()
        self.lga_repo: LGARepo = LGARepo(db)
        self.permission: CheckRolePermission = CheckRolePermission()
        self.mapper: ORMMapper = ORMMapper()
        self.fire_and_forget: AsyncioProperty = AsyncioProperty()

    async def check_owner(self, property_id: uuid.UUID, user_id: uuid.UUID):
        prop = await self.repo.get_by_id(property_id)
        if not prop:
            raise HTTPException(404, "Property not found")

        if prop.owner_id != user_id:
            raise HTTPException(
                403, "You are not allowed to update or delete this property"
            )
        return prop

    async def create_property(self, data, current_user):
        async def handler():
            # await self.permission.check_landlord_or_admin(current_user=current_user)
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
                default_rent_amount=data.default_rent_amount,
                default_rent_cycle=data.default_rent_cycle,
                house_type=data.house_type,
                property_type=data.property_type,
                square_meters=data.square_meters,
                is_owner=data.is_owner,
                is_manager=data.is_manager,
                managed_by_id=data.managed_by_id,
            )
            prop = await self.repo.get_property_with_relations(props.id)

            asyncio.create_task(
                self.fire_and_forget.create(
                    prop=prop, user_id=user_id, property_id=props.id
                )
            )
            return self.mapper.one(prop, PropertyOut)

        return await breaker.call(handler)

    async def update_property(self, property_id: uuid.UUID, current_user, data):
        async def handler():
            user_id = current_user.id

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
            asyncio.create_task(
                self.fire_and_forget.update(
                    prop=prop, user_id=user_id, property_id=new_prop.id
                )
            )

            return self.mapper.one(prop, PropertyOut)

        return await breaker.call(handler)

    async def delete_property(self, user_id: uuid.UUID, property_id: uuid.UUID):
        async def handler():
            prop = await self.check_owner(property_id=property_id, user_id=user_id)
            
            await self.repo.delete_property(user_id=user_id, property_id=property_id)

            asyncio.create_task(
                self.fire_and_forget.create(
                    prop=prop, user_id=user_id, property_id=property_id
                )
            )
            return JSONResponse(
                {
                    "message": "Delete successful",
                }
            )

        return await breaker.call(handler)

    async def get_property_by_state_user(
        self, property_id: uuid.UUID, state_id: uuid.UUID, current_user
    ) -> PropertyOut:
        async def handler():
            user_id = current_user.id
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
        self, state_id: uuid.UUID, user_id: uuid.UUID, page: int = 1, per_page: int = 20
    ) -> List[PropertyOut]:
        async def handler():
            
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

    async def get_properties_by_lga_user(
        self,
        lga_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> List[PropertyOut]:
        async def handler():
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
        user_id: uuid.UUID,
    ) -> Optional[PropertyOut]:
        async def handler():
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
