import logging
import uuid

import httpx


from celery import shared_task

from core.get_db import SyncSessionLocal
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

    return process_payment(payment_id=payment_uuid)

def process_payment(payment_id: uuid.UUID):
    db=SyncSessionLocal()
    try:
        return  AutoPayoutService(db).process_payment(payment_id)
    except Exception:
        db.rollback()
    finally:
        db.close()