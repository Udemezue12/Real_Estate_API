from fintechs.flutterwave import FlutterwaveClient
from models.enums import PaymentProvider, PaymentStatus
from repos.payment_transaction_repo import PaymentTransactionRepo
import uuid
from fastapi import HTTPException


class ProcessPaymentService:
    def __init__(self, db):
        self.db = db
        self.repo = PaymentTransactionRepo(db)
        self.flutterwave = FlutterwaveClient()

    async def process_flutterwave_payment(self, payment_id: uuid.UUID, reference: str):
        verification = await self.flutterwave.verify_payment(reference)

        if not verification.get("success"):
            await self.repo.update_status_provider(
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                payment_provider=PaymentProvider.NONE_YET,
            )
            raise HTTPException(400, "Failed")

        flw_ref = verification.get("flw_ref")

        if flw_ref:
            await self.repo.set_reference(payment_id, flw_ref)
        
        await self.repo.update_status_provider(
            payment_id=payment_id,
            status=PaymentStatus.VERIFIED,
            payment_provider=PaymentProvider.FLUTTERWAVE,
        )

        return verification
