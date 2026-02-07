import dramatiq

from core.get_db import AsyncSessionLocal
from services.generate_receipt_service import GenerateReceiptPDF


def create_receipt_task():
    @dramatiq.actor(
        queue_name="generate_receipt_pdf",
        max_retries=3,
        time_limit=600_000,
    )
    async def generate_receipt(receipt_id: str):
        async with AsyncSessionLocal() as db:
            return await GenerateReceiptPDF(db).generate_and_upload(
                receipt_id=receipt_id
            )

    return generate_receipt
