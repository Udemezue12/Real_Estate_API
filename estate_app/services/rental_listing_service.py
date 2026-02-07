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
from models.models import RentalListing
from repos.lga_repos import LGARepo
from repos.rental_images_repo import RentalListingImageRepo
from repos.rental_listing_repo import RentalListingRepo
from schemas.schema import RentalListingOut


class RentalListingService:
    LOCK_KEY = "property-rentals-service-lock-v2"

    def __init__(self, db):
        self.repo: RentalListingRepo = RentalListingRepo(db)
        self.lga_repo: LGARepo = LGARepo(db)
        self.image_repo: RentalListingImageRepo = RentalListingImageRepo(db)
        self.paginate: PaginatePage = PaginatePage()
        self.mapper: ORMMapper = ORMMapper()
        self.permission: CheckRolePermission = CheckRolePermission()
        self.idempotency: RedisIdempotency = RedisIdempotency(
            namespace="property-rentals-service"
        )

    async def check_lists_exists(
        self, listing_id: uuid.UUID, current_user
    ) -> RentalListing:
        listing = await self.repo.get_listing_id(listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        if listing.listed_by_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not Allowed",
            )
        return listing

    async def get_all_listings(
        self,
        current_user,
        page: int = 1,
        per_page: int = 20,
    ) -> List[RentalListingOut]:
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"rental_listings:all:{page}:{per_page}"

            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.many(items=cached, schema=RentalListingOut)
            listings = await self.repo.get_all()
            listings_out = self.mapper.many(items=listings, schema=RentalListingOut)
            paginated = self.paginate.paginate(listings_out, page, per_page)

            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated),
                ttl=300,
            )
            return paginated

        return await breaker.call(handler)

    async def get_listing(self, listing_id: uuid.UUID, current_user):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"sale_listing:{listing_id}"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.one(cached, RentalListingOut)

            listing = await self.repo.get_listing_id(listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")

            listing_out = self.mapper.one(listing, RentalListingOut)

            await cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(listing_out),
                ttl=300,
            )

            return listing_out

        return await breaker.call(handler)

    async def create_listing(self, data: dict, current_user):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            existing = await self.repo.get_by_address(address=data.address)
            if existing:
                raise HTTPException(
                    status_code=400, detail="Property already exists in this address"
                )

            data_dict = data.model_dump()

            data_dict["listed_by_id"] = current_user.id
            data_dict["rental_listed_by"] = current_user.id
            data_dict["contact_phone"] = current_user.phone_number
            data_dict["is_verified"] = False

            await self.lga_repo.validate_state_lga_match(
                state_id=data_dict["state_id"],
                lga_id=data_dict["lga_id"],
            )

            listing = await self.repo.create(data_dict)

            listing_id = listing.id
            listing_out = self.mapper.one(listing, RentalListingOut)

            await publish_event(
                "rental_listing.created",
                {
                    "listing_id": str(listing.id),
                    "title": listing.title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            await cache.delete_cache_keys_async(
                "rental_listings:all",
                f"rental_listings:state:{listing.state_id}",
                f"rental_listings:lga:{listing.lga_id}",
                f"rental_listing:{listing_id}",
            )

            return listing_out

        return await breaker.call(handler)

    async def update_listing(self, listing_id: uuid.UUID, data, current_user):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            await self.check_lists_exists(
                listing_id=listing_id, current_user=current_user
            )
            updated_data = data.model_dump(exclude_unset=True)
            if not updated_data:
                raise HTTPException(
                    status_code=400,
                    detail="No fields provided for update.",
                )
            state_id = updated_data.get("state_id")
            lga_id = updated_data.get("lga_id")

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
                "rental_listing.updated",
                {
                    "listing_id": str(updated.id),
                    "title": updated.title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            await cache.delete_cache_keys_async(
                "rental_listings:all",
                f"rental_listings:state:{state_id}",
                f"rental_listings:lga:{lga_id}",
                f"rental_listing:{listing_id}",
            )

            return self.mapper.one(prop, RentalListingOut)

        return await breaker.call(handler)

    async def delete_listing(self, listing_id: uuid.UUID, current_user):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            listing = await self.check_lists_exists(
                listing_id=listing_id, current_user=current_user
            )
            await self.repo.delete(listing_id=listing_id, user_id=current_user.id)
            lga_id = listing.lga_id
            state_id = listing.state_id

            await publish_event(
                "rental_listing.deleted",
                {
                    "listing_id": str(listing.id),
                    "title": listing.title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            await cache.delete_cache_keys_async(
                "rental_listings:all",
                f"rental_listings:state:{state_id}",
                f"rental_listings:lga:{lga_id}",
                f"rental_listing:{listing_id}",
            )

            return {"deleted": True, "id": str(listing.id)}

        return await breaker.call(handler)

    async def delete_all_listings(self, current_user):
        async def handler():
            await self.permission.check_admin(current_user=current_user)
            listing = await self.repo.delete_all()
            listing_id = listing.id
            lga_id = listing.lga_id
            state_id = listing.state_id

            await publish_event(
                "rental_listing.deleted_all",
                {"timestamp": datetime.now(timezone.utc).isoformat()},
            )

            await cache.delete_cache_keys_async(
                "rental_listings:all",
                f"rental_listings:state:{state_id}",
                f"rental_listings:lga:{lga_id}",
                f"rental_listing:{listing_id}",
            )

            return {"deleted": True, "message": "All listings deleted"}

        return await breaker.call(handler)

    async def get_properties_by_state(
        self,
        state_id: uuid.UUID,
        current_user,
        page: int = 1,
        per_page: int = 20,
    ) -> List[RentalListingOut]:
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"rental_listings:state:{state_id}:page:{page}:per:{per_page}"

            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.many(cached, RentalListingOut)
            listings = await self.repo.get_by_state(
                state_id, page=page, per_page=per_page
            )

            listings_out = self.mapper.many(listings, RentalListingOut)

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
        current_user,
        page: int = 1,
        per_page: int = 20,
    ) -> List[RentalListingOut]:
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            cache_key = f"rental_listings:lga:{lga_id}:page:{page}:per:{per_page}"

            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.many(cached, RentalListingOut)
            listings = await self.repo.get_by_lga(lga_id, page=page, per_page=per_page)

            listings_out = self.mapper.many(listings, RentalListingOut)

            paginated = self.paginate.paginate(listings_out, page, per_page)

            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated),
                ttl=300,
            )
            return paginated

        return await breaker.call(handler)

    async def mark_as_available(
        self,
        listing_id: uuid.UUID,
        current_user,
    ):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            listing = await self.repo.get_listing_id(listing_id)
            if not listing:
                raise HTTPException(404, "Not Found")
            sold = await self.repo.mark_as_available(
                listing_id=listing_id, user_id=current_user.id
            )
            if not sold:
                raise HTTPException(404, "Listing not found or already available")
            await cache.delete_cache_keys_async(
                "rental_listings:all",
                f"rental_listings:state:{listing.state_id}",
                f"rental_listings:lga:{listing.lga_id}",
                f"rental_listing:{listing_id}",
            )

            await publish_event(
                "rent_listing.is_available",
                {
                    "listing_id": str(listing.id),
                    "title": listing.title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            return {"message": "Property Now Available for Rent"}

        return await breaker.call(handler)

    async def mark_as_unavailable(
        self,
        listing_id: uuid.UUID,
        current_user,
    ):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            listing = await self.repo.get_listing_id(listing_id)
            if not listing:
                raise HTTPException(404, "Not Found")
            sold = await self.repo.mark_as_unavailable(
                listing_id=listing_id, user_id=current_user.id
            )
            if not sold:
                raise HTTPException(404, "Listing not found or already unavailable")
            await cache.delete_cache_keys_async(
                "rental_listings:all",
                f"rental_listings:state:{listing.state_id}",
                f"rental_listings:lga:{listing.lga_id}",
                f"rental_listing:{listing_id}",
            )

            await publish_event(
                "rental_listing.is_unavailable",
                {
                    "listing_id": str(listing.id),
                    "title": listing.title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            return {"message": "Property Unavailable for Rent"}

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
                property_id=property_id,
                is_verified=True,
                verified_by_id=current_user.id,
            )
            await cache.delete_cache_keys_async(
                "sale_listings:all",
                f"sale_listings:state:{property.state_id}",
                f"sale_listings:lga:{property.lga_id}",
                f"sale_listing:{property_id}",
            )
            return {"message": "Verified Successfully"}

        return await self.idempotency.run_once(key=self.LOCK_KEY, coro=_start, ttl=120)
