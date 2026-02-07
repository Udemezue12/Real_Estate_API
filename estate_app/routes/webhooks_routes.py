from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from webhooks.service_webhooks import PaymentWebhooks

router = APIRouter(tags=["Webhooks"])


@cbv(router)
class WebhookRoutes:
    @router.post("/webhooks/flutterwave", dependencies=[rate_limit])
    @safe_handler
    async def flutterwave_webhook(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PaymentWebhooks(db=db, request=request).flutterwave_webhook(
            background_tasks
        )

    @router.post("/webhooks/paystack", dependencies=[rate_limit])
    @safe_handler
    async def paystack_webhook(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PaymentWebhooks(db=db, request=request).paystack_webhook(
            background_tasks
        )
