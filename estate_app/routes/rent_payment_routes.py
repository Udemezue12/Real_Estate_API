import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from models.models import User
from schemas.schema import (
    RentPaymentSchema,
)
from services.rent_payment_service import RentPaymentService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Make Online Rent Payments and Manual Verifications"])


@cbv(router)
class PaymentsRoutes:
    @router.post(
        "/initalize/payment",
        dependencies=[rate_limit],
    )
    @safe_handler
    async def initialize_payments(
        self,
        data: RentPaymentSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentPaymentService(db).process_rent_payment(
            current_user,
            data=data,
        )

    @router.post("/{reference}/verify-payment", dependencies=[rate_limit])
    @safe_handler
    async def verify_payments(
        self,
        reference: str,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentPaymentService(db).verify_payment(
            background_tasks=background_tasks,
            current_user=current_user,
            reference=reference
        )

    @router.post(
        "/refund-payments/{payment_id}",
        dependencies=[rate_limit],
    )
    @safe_handler
    async def refund_payment_endpoint(
        self,
        payment_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentPaymentService(db).refund_payment(
            payment_id=payment_id, current_user=current_user
        )
