import uuid

import dramatiq

from core.get_db import AsyncSessionLocal
from services.autopayout_service import AutoPayoutService


def create_auto_payout_task():
    @dramatiq.actor(
        queue_name="auto_payout_landlord",
        max_retries=3,
        time_limit=600_000,
    )
    async def process_payment(payment_id: uuid.UUID):
        async with AsyncSessionLocal() as db:
            return await AutoPayoutService(db).process_payment(payment_id)

    return process_payment
