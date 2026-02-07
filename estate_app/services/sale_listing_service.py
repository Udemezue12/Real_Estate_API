import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException

from core.breaker import breaker
from core.cache import cache
from core.check_permission import CheckRolePermission
from core.event_publish import publish_event
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from core.redis_idempotency import RedisIdempotency
from models.enums import SOLD_BY
from models.models import SaleListing
from repos.lga_repos import LGARepo
from repos.sale_listing_repo import SaleListingRepo
from repos.sales_images_repo import SaleListingImageRepo
from schemas.schema import SalesListingOut


class SaleListingService:
    LOCK_KEY = "property-sales-service-lock-v2"

    def __init__(self, db):
        self.repo: SaleListingRepo = SaleListingRepo(db)
        self.lga_repo: LGARepo = LGARepo(db)
        self.permission: CheckRolePermission = CheckRolePermission()
        self.idempotency: RedisIdempotency = RedisIdempotency(
            namespace="property-sales-service"
        )
        self.image_repo: SaleListingImageRepo = SaleListingImageRepo(db=db)
        self.paginate: PaginatePage = PaginatePage()
        self.mapper: ORMMapper = ORMMapper()

    async def check_lists_exists(
        self, listing_id: uuid.UUID, current_user, is_available: bool = False
    ) -> SaleListing:
        listing = await self.repo.get_listing_id(listing_id)

        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        if listing.listed_by_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not Allowed",
            )
        if listing.is_available == is_available:
            raise HTTPException(400, "This property has been sold and cant be deleted")

        return listing

    async def get_all_listings(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> List[SalesListingOut]:
        async def handler():
            cache_key = f"sale_listings:all:{page}:{per_page}"

            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.many(items=cached, schema=SalesListingOut)
            listings = await self.repo.get_all()
            listings_out = self.mapper.many(items=listings, schema=SalesListingOut)
            paginated = self.paginate.paginate(listings_out, page, per_page)

            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated),
                ttl=300,
            )
            return paginated

        return await breaker.call(handler)

    async def get_all_sold_listings(
        self,
        current_user,
        page: int = 1,
        per_page: int = 20,
    ) -> List[SalesListingOut]:
        async def handler():
            user_id = current_user.id
            cache_key = f"sale_listings:sold:{user_id}:{page}:{per_page}"

            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.many(items=cached, schema=SalesListingOut)
            listings = await self.repo.get_sold_properties(user_id=user_id)
            listings_out = self.mapper.many(items=listings, schema=SalesListingOut)
            paginated = self.paginate.paginate(listings_out, page, per_page)

            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated),
                ttl=300,
            )
            return paginated

        return await breaker.call(handler)

    async def get_listing(self, listing_id: uuid.UUID):
        async def handler():
            cache_key = f"sale_listing:{listing_id}"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.one(cached, SalesListingOut)

            listing = await self.repo.get_listing_id(listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")

            listing_out = self.mapper.one(listing, SalesListingOut)

            await cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(listing_out),
                ttl=300,
            )

            return listing_out

        return await breaker.call(handler)

    async def create_listing(self, data: dict, current_user):
        async def handler():
            existing = await self.repo.get_by_address(address=data.address)
            if existing:
                raise HTTPException(
                    status_code=400, detail="Property already exists in this address"
                )

            data_dict = data.model_dump()

            data_dict["listed_by_id"] = current_user.id
            data_dict["sale_listed_by"] = current_user.id
            data_dict["contact_phone"] = current_user.phone_number
            data_dict["sold_by"] = SOLD_BY.NOT_SOLD
            data_dict["is_verified"] = False
            await self.lga_repo.validate_state_lga_match(
                state_id=data_dict["state_id"],
                lga_id=data_dict["lga_id"],
            )

            listing = await self.repo.create(data_dict)

            listing_id = listing.id
            listing_out = self.mapper.one(listing, SalesListingOut)

            await publish_event(
                "sale_listing.created",
                {
                    "listing_id": str(listing.id),
                    "title": listing.title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            await cache.delete_cache_keys_async(
                "sale_listings:all",
                f"sale_listings:state:{listing.state_id}",
                f"sale_listings:lga:{listing.lga_id}",
                f"sale_listing:{listing_id}",
                f"sale_listings:sold:{current_user.id}",
            )

            return listing_out

        return await breaker.call(handler)

    async def update_listing(self, listing_id: uuid.UUID, data, current_user):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            # await self.check_lists_exists(
            #     listing_id=listing_id, current_user=current_user
            # )
            updated_data = data.model_dump(exclude_unset=True)
            if not updated_data:
                raise HTTPException(
                    status_code=400,
                    detail="No fields provided for update.",
                )
            state_id = updated_data.get("state_id")
            lga_id = updated_data.get("lga_id")
            updated_data["updated_at"] = datetime.utcnow()

            if state_id is not None and lga_id is not None:
                await self.lga_repo.validate_state_lga_match(
                    state_id=state_id,
                    lga_id=lga_id,
                )

            updated = await self.repo.update(
                user_id=user_id,
                listing_id=listing_id,
                **updated_data,
            )

            if not updated:
                raise HTTPException(
                    status_code=404, detail="Listing not found or not modified"
                )
            prop = await self.repo.get_property_with_relations(updated.id)
            lga_id = updated.lga_id
            state_id = updated.state_id

            await publish_event(
                "sale_listing.updated",
                {
                    "listing_id": str(updated.id),
                    "title": updated.title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            await cache.delete_cache_keys_async(
                "sale_listings:all",
                f"sale_listings:state:{state_id}",
                f"sale_listings:lga:{lga_id}",
                f"sale_listing:{listing_id}",
                f"sale_listings:sold:{current_user.id}",
            )

            return self.mapper.one(prop, SalesListingOut)

        return await breaker.call(handler)

    async def delete_listing(
        self,
        listing_id: uuid.UUID,
        current_user,
    ):
        async def handler():
            await self.check_lists_exists(listing_id, current_user)

            listing = await self.repo.delete(
                listing_id=listing_id, user_id=current_user.id
            )
            lga_id = listing.lga_id
            state_id = listing.state_id

            await publish_event(
                "sale_listing.deleted",
                {
                    "listing_id": str(listing.id),
                    "title": listing.title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            await cache.delete_cache_keys_async(
                "sale_listings:all",
                f"sale_listings:state:{state_id}",
                f"sale_listings:lga:{lga_id}",
                f"sale_listing:{listing_id}",
                f"sale_listings:sold:{current_user.id}",
            )

            return {"deleted": True, "id": str(listing.id)}

        return await breaker.call(handler)

    async def delete_all_listings(self):
        async def handler():
            listing = await self.repo.delete_all()
            listing_id = listing.id
            lga_id = listing.lga_id
            state_id = listing.state_id

            await publish_event(
                "sale_listing.deleted_all",
                {"timestamp": datetime.now(timezone.utc).isoformat()},
            )

            await cache.delete_cache_keys_async(
                "sale_listings:all",
                f"sale_listings:state:{state_id}",
                f"sale_listings:lga:{lga_id}",
                f"sale_listing:{listing_id}",
            )

            return {"deleted": True, "message": "All listings deleted"}

        return await breaker.call(handler)

    async def get_properties_by_state(
        self,
        state_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> List[SalesListingOut]:
        async def handler():
            cache_key = f"sale_listings:state:{state_id}:page:{page}:per:{per_page}"

            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.many(cached, SalesListingOut)

            listings = await self.repo.get_by_state(
                state_id=state_id, page=page, per_page=per_page
            )

            listings_out = self.mapper.many(listings, SalesListingOut)
            if not listings:
                return []

            paginated = self.paginate.paginate(listings_out, page, per_page)

            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated),
                ttl=300,
            )
            return paginated

        return await breaker.call(handler)

    async def get_properties_by_lga(
        self,
        lga_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> List[SalesListingOut]:
        async def handler():
            cache_key = f"sale_listings:lga:{lga_id}:page:{page}:per:{per_page}"

            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            listings = await self.repo.get_by_lga(lga_id, page=page, per_page=per_page)

            listings_out = self.mapper.many(listings, SalesListingOut)

            paginated = self.paginate.paginate(listings_out, page, per_page)

            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated),
                ttl=300,
            )
            return paginated

        return await breaker.call(handler)

    async def mark_as_sold(self, listing_id: uuid.UUID, current_user, data):
        async def handler():
            listing = await self.check_lists_exists(listing_id, current_user)
            sold = await self.repo.mark_as_sold(
                listing_id=listing_id,
                user_id=current_user.id,
                sold_by=data.sold_by,
                is_available=False,
            )
            if not sold:
                raise HTTPException(404, "Listing not found or already sold")

            await cache.delete_cache_keys_async(
                "sale_listings:all",
                f"sale_listings:state:{listing.state_id}",
                f"sale_listings:lga:{listing.lga_id}",
                f"sale_listing:{listing_id}",
                f"sale_listings:sold:{current_user.id}",
            )
            await publish_event(
                "sale_listing.sold",
                {
                    "listing_id": str(listing.id),
                    "title": listing.title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            return {"message": "Successfully Sold"}

        return await breaker.call(handler)

    async def unmark_as_sold(self, listing_id: uuid.UUID, current_user):
        async def handler():
            listing = await self.check_lists_exists(listing_id, current_user)
            sold = await self.repo.mark_as_sold(
                listing_id=listing_id,
                user_id=current_user.id,
                sold_by=SOLD_BY.NOT_SOLD,
                is_available=True,
            )
            if not sold:
                raise HTTPException(404, "Listing not found")

            await cache.delete_cache_keys_async(
                "sale_listings:all",
                f"sale_listings:state:{listing.state_id}",
                f"sale_listings:lga:{listing.lga_id}",
                f"sale_listing:{listing_id}",
                f"sale_listings:sold:{current_user.id}",
            )
            await publish_event(
                "sale_listing.unsold",
                {
                    "listing_id": str(listing.id),
                    "title": listing.title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            return {"message": "Successfully Done"}

        return await breaker.call(handler)

    async def mark_as_verified(self, property_id: uuid.UUID, current_user):
        async def _start():
            await self.permission.check_admin(current_user=current_user)
            property = await self.repo.get_listing_id(property_id)
            if not property:
                raise HTTPException(404, "Not Found")
            if property.is_verified:
                raise HTTPException(403, "This property has already been verified")
            await self.repo.mark_property_verified(
                property_id=property_id, is_verified=True
            )
            await cache.delete_cache_keys_async(
                "sale_listings:all",
                f"sale_listings:state:{property.state_id}",
                f"sale_listings:lga:{property.lga_id}",
                f"sale_listing:{property_id}",
                f"sale_listings:sold:{property.listed_by_id}",
            )
            return {"message": "Verified Successfully"}

        return await self.idempotency.run_once(key=self.LOCK_KEY, coro=_start, ttl=120)
