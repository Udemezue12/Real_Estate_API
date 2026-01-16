import uuid

from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.idempotency_provider import get_idem_key
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import TenantCreate, TenantUpdate, TenantWithPropertyOut
from services.tenant_service import TenantService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Tenants Management"])


@cbv(router=router)
class TenantsRoutes:
    @router.post(
        "/create", dependencies=[rate_limit], response_model=TenantWithPropertyOut
    )
    @safe_handler
    async def create(
        self,
        payload: TenantCreate,
        current_user: User = Depends(get_current_user),
        idem_key: str = Depends(get_idem_key),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await TenantService(db).create_tenant(
            current_user=current_user, payload=payload, idem_key=idem_key
        )

    @router.patch(
        "/{tenant_id}", response_model=TenantWithPropertyOut, dependencies=[rate_limit]
    )
    @safe_handler
    async def update(
        self,
        tenant_id: uuid.UUID,
        payload: TenantUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await TenantService(db).update_tenant(
            tenant_id=tenant_id,
            payload=payload,
            current_user=current_user,
        )

    @router.delete("/{tenant_id}/delete", dependencies=[rate_limit])
    @safe_handler
    async def delete(
        self,
        tenant_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        idem_key: str = Depends(get_idem_key),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await TenantService(db).delete_tenant(
            current_user=current_user, tenant_id=tenant_id, idem_key=idem_key
        )

    @router.get(
        "/tenants/{tenant_id}/get",
        dependencies=[rate_limit],
        response_model=TenantWithPropertyOut,
    )
    @safe_handler
    async def get_tenant(
        self,
        tenant_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await TenantService(db).get_tenant(
            tenant_id=tenant_id,
            current_user=current_user,
        )

    @router.get("/property/{property_id}/all", dependencies=[rate_limit])
    @safe_handler
    async def all_tenants(
        self,
        property_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await TenantService(db).list_tenants_for_property(
            property_id=property_id,
            current_user=current_user,
        )

    @router.get("/admin/all", dependencies=[rate_limit])
    @safe_handler
    async def get_all_tenants_admin(
        self,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await TenantService(db).admin_list_all_tenants(
            current_user=current_user,
        )
