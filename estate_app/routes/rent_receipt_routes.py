import uuid

from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from models.models import User
from schemas.schema import RejectProofSchema, RentReceiptBaseOut
from services.rent_receipt_service import RentReceiptService

router = APIRouter(tags=["Rent Receipts"])


@cbv(router=router)
class RentReceiptRoutes:
    @router.post("/{proof_id}/mark_as_paid", dependencies=[rate_limit])
    @safe_handler
    async def mark_as_paid(
        self,
        proof_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentReceiptService(db).mark_as_paid(
            current_user=current_user,
            proof_id=proof_id,
        )

    @router.post("/{proof_id}/reject_proof", dependencies=[rate_limit])
    @safe_handler
    async def reject_proof(
        self,
        proof_id: uuid.UUID,
        data: RejectProofSchema,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentReceiptService(db).reject_proof(
            current_user=current_user, proof_id=proof_id, data=data
        )

    @router.get("/{receipt_id}/download", dependencies=[rate_limit])
    @safe_handler
    async def download_receipt(
        self,
        receipt_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentReceiptService(db).download_receipt(
            current_user=current_user, receipt_id=receipt_id
        )

    @router.get("/verify", dependencies=[rate_limit])
    @safe_handler
    async def verify_receipt(
        self,
        reference: str,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentReceiptService(db).verify_receipt(
            current_user=current_user, reference=reference
        )

    @router.get(
        "/tenant/{tenant_id}/{receipt_id}/get",
        dependencies=[rate_limit],
        response_model=RentReceiptBaseOut,
    )
    @safe_handler
    async def get_tenant_receipt(
        self,
        tenant_id: uuid.UUID,
        receipt_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentReceiptService(db).get_tenant_receipt(
            current_user=current_user,
            tenant_id=tenant_id,
            receipt_id=receipt_id,
        )

    @router.get(
        "/tenant/{property_id}",
        dependencies=[rate_limit],
        response_model=list[RentReceiptBaseOut],
    )
    @safe_handler
    async def get_tenant_receipts_for_property(
        self,
        property_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentReceiptService(db).get_tenant_receipts_for_property(
            current_user=current_user,
            property_id=property_id,
            page=page,
            per_page=per_page,
        )

    @router.get(
        "/property/{property_id}",
        dependencies=[rate_limit],
        response_model=list[RentReceiptBaseOut],
    )
    @safe_handler
    async def get_property_receipts(
        self,
        property_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentReceiptService(db).get_property_receipts(
            current_user=current_user,
            property_id=property_id,
            page=page,
            per_page=per_page,
        )

    @router.get(
        "/property/{property_id}/{receipt_id}",
        dependencies=[rate_limit],
        response_model=RentReceiptBaseOut,
    )
    @safe_handler
    async def get_property_receipt(
        self,
        property_id: uuid.UUID,
        receipt_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentReceiptService(db).get_receipt_for_property_owner_or_manager(
            current_user=current_user,
            property_id=property_id,
            receipt_id=receipt_id,
        )

    @router.delete(
        "/{receipt_id}/delete",
        dependencies=[rate_limit],
    )
    @safe_handler
    async def delete_receipt(
        self,
        receipt_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentReceiptService(db).delete(
            current_user=current_user,
            receipt_id=receipt_id,
        )
