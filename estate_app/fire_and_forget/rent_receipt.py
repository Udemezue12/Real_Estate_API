from celery_worker.celery_app import app as task_app
from core.cache import cache
from core.event_publish import publish_event


class AsyncioRentReceipt:
    async def mark_as_paid(
        self,
        receipt,
        tenant,
    ):
        task_app.send_task(
            "generate_receipt_pdf",
            args=[str(receipt.id)],
        )

        await cache.delete_cache_keys_async(
            f"tenant:{tenant.id}:receipt:{receipt.id}:property"
            f"tenant:{tenant.id}:receipts:property:{receipt.property_id}",
            f"property:{receipt.property_id}:receipts ",
            f"property:{receipt.property_id}:receipt:{receipt.id}",
        )

        await publish_event(
            "rent_receipts.created",
            {
                "receipt_id": str(receipt.id),
                "tenant_id": str(tenant.id),
            },
        )
