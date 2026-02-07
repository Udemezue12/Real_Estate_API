import logging
import uuid

import httpx
from asyncio import run as async_run

from celery import shared_task

from core.get_db import AsyncSessionLocal
from services.autopayout_service import AutoPayoutService

logger = logging.getLogger("auto_payouts")





@shared_task(
    name="auto_payout_landlord",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_auto_payout_task(
    payment_id: str,
):
    payment_uuid = uuid.UUID(payment_id)

    if not payment_uuid:
        raise ValueError("Invalid payment_id")

    return async_run(process_payment(payment_id=payment_uuid))

async def process_payment(payment_id: uuid.UUID):
    async with AsyncSessionLocal() as db:
        return await AutoPayoutService(db).process_payment(payment_id)