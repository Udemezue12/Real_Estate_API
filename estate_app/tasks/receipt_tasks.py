import logging
import uuid

import httpx
from asyncio import run as async_run

from celery import shared_task

from core.get_db import AsyncSessionLocal
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
    return async_run(generate_and_upload(receipt_uuid))
async def generate_and_upload(
            receipt_id: uuid.UUID,
        ):
            async with AsyncSessionLocal() as session:
                return await GenerateReceiptPDF(session).generate_and_upload(receipt_id)