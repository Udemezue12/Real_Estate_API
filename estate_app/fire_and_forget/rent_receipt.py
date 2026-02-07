from core.cache import cache
from core.event_publish import publish_event
from email_notify.email_service import EmailService
from sms_notify.sms_service import TermiiClient
from tasks.receipt_tasks import create_receipt_tasks


class AsyncioRentReceipt:
    def __init__(self):
        self.sms_service: TermiiClient = TermiiClient()
        self.email_service: EmailService = EmailService()

    async def mark_as_paid(
        self,
        receipt,
        tenant,
    ):
       

        create_receipt_tasks.delay(str(receipt.id))

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

    async def mark_paid(
        self,
        receipt,
        tenant,
        email: str,
        landlord_name: str,
        tenant_name: str,
    ):
        

        create_receipt_tasks.delay(str(receipt.id))

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
        await self.email_service.send_rent_processed_mail(
            email=email,
            landlord_name=landlord_name,
            tenant_name=tenant_name,
            path=receipt.receipt_path,
        )
