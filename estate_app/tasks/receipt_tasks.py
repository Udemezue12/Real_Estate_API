import logging
import uuid

import httpx


from celery import shared_task

from core.get_db import SyncSessionLocal
from services.generate_receipt_service import GenerateReceiptPDF

logger = logging.getLogger("receipts.pdf")


@shared_task(
    name="generate_receipt_pdf",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries":3}
)
def create_receipt_tasks(receipt_id:str):
    receipt_uuid = uuid.UUID(receipt_id)

    if not receipt_uuid:
                raise ValueError("Invalid receipt_id")
    return generate_and_upload(receipt_uuid)
def generate_and_upload(
            receipt_id: uuid.UUID,
        ):
            db = SyncSessionLocal()
            try:
                return GenerateReceiptPDF(db).generate_and_upload(receipt_id)
            except Exception:
                db.rollback()
            finally:
                db.close()
            