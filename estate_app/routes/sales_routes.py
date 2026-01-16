import uuid
from typing import List
from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import SalesListingOut, SalesListingSchema,SalesListingUpdateSchema,MarkAsSoldSchema
from services.sale_listing_service import SaleListingService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Property Listing For Sale"])


@cbv(router=router)
class SalesRoutes:
    @router.get(
        "/all",
        dependencies=[rate_limit],
        response_model=List[SalesListingOut],
    )
    @safe_handler
    async def get_all(
        self,
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await SaleListingService(db).get_all_listings(page, per_page)
    @router.get(
        "/sold",
        dependencies=[rate_limit],
        response_model=List[SalesListingOut],
    )
    @safe_handler
    async def get_sold_properties(
        self,
        current_user: User = Depends(get_current_user),
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await SaleListingService(db).get_sold_properties(current_user=current_user, page=page, per_page=per_page)

    @router.get(
        "/listings/{listing_id}/get", dependencies=[rate_limit], response_model=SalesListingOut
    )
    @safe_handler
    async def get(
        self,
        listing_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await SaleListingService(db).get_listing(listing_id=listing_id)

    @router.get(
        "/states/{state_id}/get",
        dependencies=[rate_limit],
        response_model=List[SalesListingOut],
    )
    @safe_handler
    async def get_all_by_state(
        self,
        state_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await SaleListingService(db).get_properties_by_state(
            state_id=state_id, page=page, per_page=per_page
        )

    @router.get(
        "/lgas/{lga_id}/get", dependencies=[rate_limit], response_model=List[SalesListingOut]
    )
    @safe_handler
    async def get_all_by_lga(
        self,
        lga_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await SaleListingService(db).get_properties_by_lga(lga_id=lga_id, page=page, per_page=per_page)

    @router.post("/create", dependencies=[rate_limit], response_model=SalesListingOut)
    @safe_handler
    async def create(
        self,
        data: SalesListingSchema,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await SaleListingService(db).create_listing(
            data=data, current_user=current_user
        )
    @router.patch("/{listing_id}/update", dependencies=[rate_limit], response_model=SalesListingOut)
    @safe_handler
    async def update(
        self,
        listing_id: uuid.UUID,
        data: SalesListingUpdateSchema,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await SaleListingService(db).update_listing(
            data=data, current_user=current_user, listing_id=listing_id
        )
    @router.post("/{listing_id}/mark_as_sold", dependencies=[rate_limit])
    @safe_handler
    async def mark_as_sold(
        self,
        listing_id: uuid.UUID,
        data: MarkAsSoldSchema,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await SaleListingService(db).mark_as_sold(
            data=data, current_user=current_user, listing_id=listing_id
        )

    @router.delete("/{listing_id}/delete", dependencies=[rate_limit])
    @safe_handler
    async def delete(
        self,
        listing_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await SaleListingService(db).delete_listing(
            listing_id=listing_id, current_user=current_user
        )
