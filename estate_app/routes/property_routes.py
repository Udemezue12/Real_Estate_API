import uuid

from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import PropertyCreate, PropertyUpdate
from services.property_service import PropertyService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Property Management"])


@cbv(router=router)
class PropertyRoutes:
    @router.post("/create", dependencies=[rate_limit])
    @safe_handler
    async def create(
        self,
        data: PropertyCreate,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PropertyService(db).create_property(
            current_user=current_user, data=data
        )

    @router.patch("/{property_id}/update", dependencies=[rate_limit])
    @safe_handler
    async def update(
        self,
        property_id: uuid.UUID,
        data: PropertyUpdate,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PropertyService(db).update_property(
            property_id=property_id, current_user=current_user, data=data
        )

    @router.delete("/{property_id}/delete", dependencies=[rate_limit])
    @safe_handler
    async def delete_property(
        self,
        property_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        await PropertyService(db).delete_property(
            property_id=property_id, user_id=current_user.id
        )

    @router.get("/{state_id}/{property_id}/get", dependencies=[rate_limit])
    @safe_handler
    async def get_user_state_property(
        self,
        property_id: uuid.UUID,
        state_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PropertyService(db).get_property_by_state_user(
            property_id=property_id, current_user=current_user, state_id=state_id
        )

    @router.get("/{state_id}/properties", dependencies=[rate_limit])
    @safe_handler
    async def get_user_state_properties(
        self,
        state_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
        page: int = 1, 
        per_page: int = 20
    ):
        return await PropertyService(db).get_properties_by_state_user(
            user_id=current_user.id, state_id=state_id, page=page, per_page=per_page
        )

    @router.get("/{lga_id}/{property_id}/get", dependencies=[rate_limit])
    @safe_handler
    async def get_user_lga_property(
        self,
        lga_id: uuid.UUID,
        property_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PropertyService(db).get_one_property(
            user_id=current_user, property_id=property_id, lga_id=lga_id
        )

    @router.get("/{lga_id}/properties", dependencies=[rate_limit])
    @safe_handler
    async def get_user_lga_properties(
        self,
        lga_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
        page: int = 1, 
        per_page: int = 20
    ):
        return await PropertyService(db).get_properties_by_lga_user(
            lga_id=lga_id, user_id=current_user.id, page=page, per_page=per_page
        )
