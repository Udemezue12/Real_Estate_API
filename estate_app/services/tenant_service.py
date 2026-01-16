import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from core.breaker import breaker
from core.cache import cache
from core.check_permission import CheckRolePermission
from core.date_helper import calculate_expiry
from core.event_publish import publish_event
from core.paginate import PaginatePage
from fastapi import HTTPException
from repos.auth_repo import AuthRepo
from repos.tenant_repo import TenantRepo
from schemas.schema import PropertyBaseOut, TenantBaseOut, TenantWithPropertyOut
from services.rent_renewal_service import RentAmountAndRenewalService
from core.validate_enum import validate_enum
from models.enums import RentCycle as RENT_CYCLE
from repos.idempotency_repo import IdempotencyRepo

logger = logging.getLogger(__name__)


class TenantService:
    def __init__(self, db):
        self.repo: TenantRepo = TenantRepo(db)
        self.paginate: PaginatePage = PaginatePage()
        self.idem_repo: IdempotencyRepo = IdempotencyRepo(db)
        self.permission: CheckRolePermission = CheckRolePermission()
        self.update_rent_amount: RentAmountAndRenewalService = (
            RentAmountAndRenewalService(db)
        )
        self.auth_repo: AuthRepo = AuthRepo(db)

    async def assert_property_owner_or_manager(self, current_user, prop):
        async def handler():
            if getattr(current_user, "is_admin", False):
                return

            if current_user.id not in {prop.owner_id, prop.managed_by_id}:
                raise HTTPException(
                    status_code=403, detail="Not permitted for this property"
                )

        return await breaker.call(handler)

    async def create_tenant(
        self, payload, current_user, idem_key=str
    ) -> TenantWithPropertyOut:
        async def handler():
            exists = await self.repo.tenant_exists(
                property_id=payload.property_id,
                first_name=payload.first_name,
                last_name=payload.last_name,
            )
            if exists:
                raise HTTPException(
                    status_code=409,
                    detail="Tenant already exists for this property",
                )
            existing_idem = await self.idem_repo.get(
                key=idem_key, user_id=current_user.id
            )
            if existing_idem and existing_idem.response:
                return existing_idem.response
            await self.idem_repo.save(idem_key, current_user.id, "CREATE:/tenant")

            prop = await self.repo.get_property(payload.property_id)
            await self.assert_property_owner_or_manager(current_user, prop)

            if payload.rent_amount is not None and payload.rent_amount <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="rent_amount must be greater than 0 or omitted",
                )

            rent_amount = (
                payload.rent_amount
                if payload.rent_amount is not None
                else prop.default_rent_amount
            )

            rent_cycle = validate_enum(
                payload.rent_cycle or prop.default_rent_cycle,
                RENT_CYCLE,
                field="rent_cycle",
            )

            rent_expiry = calculate_expiry(
                payload.rent_start_date,
                rent_cycle,
            )

            matched_user_id = None
            matched_phone_number = None
            matched_user_name = None
            name = f"{payload.first_name} {payload.middle_name} {payload.last_name}"

            matched_users = await self.auth_repo.find_users_by_name_strict(
                # payload.matched_user_name
                name=name
            )
            if matched_users:
                if len(matched_users) == 1:
                    matched_user_id = matched_users[0].id
                    matched_phone_number = matched_users[0].phone_number
                    matched_user_name = (
                        matched_users[0].first_name
                        + " "
                        + matched_users[0].middle_name
                        + " "
                        + matched_users[0].last_name
                    )

            else:
                logger.warning("No user matched for name: %r", matched_user_name)
            tenant_data = {
                "property_id": payload.property_id,
                "first_name": payload.first_name,
                "middle_name": payload.middle_name,
                "last_name": payload.last_name,
                "phone_number": matched_phone_number,
                "matched_user_id": matched_user_id,
                "rent_amount": rent_amount,
                "rent_cycle": rent_cycle,
                "rent_start_date": payload.rent_start_date,
                "rent_expiry_date": rent_expiry,
                "is_active": True,
            }

            created = await self.repo.create(tenant_data)
            tenant_id = created.id

            await cache.delete_cache_keys_async(
                f"tenants:property:{payload.property_id}",
                f"tenant:{tenant_id}",
                "tenants:all:*",
            )

            asyncio.create_task(
                publish_event(
                    "tenant.created",
                    {
                        "tenant_id": str(tenant_id),
                        "property_id": str(created.property_id),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

            schema = TenantWithPropertyOut.model_validate(created)
            response_dicts = await self.paginate.serialize_json_response(schema)
            await self.idem_repo.store_response(
                idem_key, response_dicts, current_user.id
            )
            return schema

        return await breaker.call(handler)

    async def update_tenant(
        self, tenant_id: UUID, payload, current_user
    ) -> TenantWithPropertyOut:
        async def handler():
            tenant = await self.repo.get_by_id(tenant_id)
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")

            prop = await self.repo.get_property(tenant.property_id)
            await self.assert_property_owner_or_manager(current_user, prop)
            new_amount = payload.rent_amount
            new_rent_cycle = payload.rent_cycle
            new_rent_expiry_date = payload.rent_expiry_date
            new_rent_start_date = payload.rent_start_date
            should_update_amount = (
                new_amount is not None and new_amount != tenant.rent_amount
            )

            if should_update_amount:
                await self.update_rent_amount.update_rent_amount(
                    new_amount=new_amount, tenant=tenant
                )

            start_date = new_rent_start_date or tenant.rent_start_date
            cycle = new_rent_cycle or tenant.rent_cycle

            if new_rent_expiry_date is not None:
                if start_date is None:
                    raise HTTPException(
                        400, "Cannot calculate expiry without a start date"
                    )
                expiry_date = new_rent_expiry_date
            elif new_rent_cycle is not None or new_rent_start_date is not None:
                expiry_date = calculate_expiry(start_date, cycle)
            else:
                expiry_date = tenant.rent_expiry_date

            await self.repo.update(
                user_id=tenant.matched_user_id,
                tenant_id=tenant_id,
                new_rent_amount=new_amount,
                new_rent_expiry_date=expiry_date,
                new_rent_start_date=new_rent_start_date,
                new_rent_cycle=new_rent_cycle,
            )

            await self.repo.db_commit()

            await cache.delete_cache_keys_async(
                f"tenants:property:{tenant.property_id}",
                f"tenant:{tenant.id}",
                "tenants:all:*",
            )
            asyncio.create_task(
                publish_event(
                    "tenant.updated",
                    {
                        "tenant_id": str(tenant.id),
                        "property_id": str(tenant.property_id),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

            return TenantWithPropertyOut.model_validate(tenant)

        return await breaker.call(handler)

    async def delete_tenant(self, tenant_id: UUID, current_user, idem_key: str) -> dict:
        async def handler():
            existing_idem = await self.idem_repo.get(
                key=idem_key, user_id=current_user.id
            )
            if existing_idem and existing_idem.response:
                return existing_idem.response
            await self.idem_repo.save(idem_key, current_user.id, "DELETE:/tenant")

            tenant = await self.repo.get_by_id(tenant_id)
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")

            prop = await self.repo.get_property(tenant.property_id)

            if current_user.id not in {prop.owner_id, prop.managed_by_id}:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to delete this tenant",
                )

            rows = await self.repo.delete(tenant_id)
            if rows == 0:
                raise HTTPException(status_code=500, detail="Failed to delete tenant")

            await cache.delete_cache_keys_async(
                f"tenants:property:{tenant.property_id}",
                f"tenant:{tenant_id}",
                "tenants:all:*",
            )

            asyncio.create_task(
                publish_event(
                    "tenant.deleted",
                    {
                        "tenant_id": str(tenant_id),
                        "property_id": str(tenant.property_id),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

            response = {"deleted": True, "tenant_id": str(tenant_id)}
            await self.idem_repo.store_response(idem_key, response, current_user.id)
            return response

        return await breaker.call(handler)

    async def get_tenant(self, tenant_id: UUID, current_user) -> TenantWithPropertyOut:
        async def handler():
            cache_key = f"tenant:{tenant_id}"
            cached = await cache.get_json(cache_key)
            if cached:
                return TenantWithPropertyOut.model_validate(cached)
            tenant = await self.repo.get_tenant_with_details(tenant_id)
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")

            if not getattr(current_user, "is_admin", False):
                await self.assert_property_owner_or_manager(
                    current_user, tenant.property
                )

            tenant_out = TenantWithPropertyOut.model_validate(tenant)

            await cache.set_json(cache_key, tenant_out.model_dump(mode="json"), ttl=300)
            return tenant_out

        return await breaker.call(handler)

    async def list_tenants_for_property(
        self,
        property_id: UUID,
        current_user,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict:
        prop = await self.repo.get_property(property_id)
        if not getattr(current_user, "is_admin", False):
            await self.assert_property_owner_or_manager(current_user, prop)

        cache_key = f"tenants:property:{property_id}:page:{page}:per:{per_page}"
        cached = await cache.get_json(cache_key)
        if cached:
            return cached

        tenants = await self.repo.get_all_by_property(property_id)
        tenant_dicts = [
            TenantWithPropertyOut.model_validate(t).model_dump(mode="json")
            for t in tenants
        ]

        paginated = self.paginate.paginate(tenant_dicts, page, per_page)

        await cache.set_json(cache_key, paginated, ttl=300)

        return paginated

    async def admin_list_all_tenants(
        self, current_user, offset: int = 0, limit: int = 100
    ) -> List[TenantWithPropertyOut]:
        async def handler():
            await self.permission.check_admin(current_user=current_user)
            cache_key = f"tenants:all:offset:{offset}:limit:{limit}"
            cached = await cache.get_json(cache_key)
            if cached:
                return [TenantWithPropertyOut.model_validate(t) for t in cached]

            tenants = await self.repo.get_all(offset=offset, limit=limit)
            tenant_list = [
                TenantWithPropertyOut.model_validate(t).model_dump(mode="json")
                for t in tenants
            ]

            await cache.set_json(cache_key, tenant_list, ttl=300)
            return [TenantWithPropertyOut.model_validate(t) for t in tenant_list]

        return await breaker.call(handler)
