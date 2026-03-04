import logging
import uuid
from decimal import Decimal

from models.enums import AccountNumberVerificationStatus, PaymentStatus, PayoutStatus
from repos.landlord_payout_repo import LandLordPayoutRepo
from repos.payment_transaction_repo import PaymentTransactionRepo
from repos.profile_repo import UserProfileRepo
from repos.property_repo import PropertyRepo
from repos.tenant_repo import TenantRepo
from services.payout_service import PayoutService
from services.rent_receipt_service import RentReceiptService

logger = logging.getLogger("auto_payouts")


class AutoPayoutService:
    def __init__(self, db):
        self.tenant_repo = TenantRepo(db)
        self.payment_repo = PaymentTransactionRepo(db)
        self.profile = UserProfileRepo(db)
        self.rent_receipt = RentReceiptService(db)
        self.payout_service = PayoutService()
        self.landlord_payout = LandLordPayoutRepo(db)
        self.property_repo = PropertyRepo(db)

    def process_payment(self, payment_id: uuid.UUID):
        payment = self.payment_repo.sync_get_payment_id(payment_id)
        if payment.status != PaymentStatus.VERIFIED:
            return
        property = self.property_repo.sync_get_by_id(payment.property_id)
        if not property:
            raise ValueError("Property not found")
        landlord_user = property.owner

        landlord_profile = self.profile.sync_get_by_user(landlord_user.id)
        if not landlord_profile:
            raise ValueError("Landlord profile missing")

        if AccountNumberVerificationStatus.VERIFIED not in (
            landlord_profile.paystack_account_verification_status,
            landlord_profile.flutterwave_account_verification_status,
        ):
            raise ValueError("Account not yet verified by any payment provider")

        if landlord_user.id != payment.landlord_id:
            raise ValueError("Landlord mismatch")
        recipient = landlord_profile.paystack_recipient_code

        if not recipient:
            raise ValueError("No recipient code")
        try:
            payout = self.landlord_payout.sync_landlord_payment_id(payment_id)
            if payout and payout.status == PayoutStatus.COMPLETED:
                return
            amount = Decimal(str(payment.amount_received))
            if not payout:
                payout =  self.landlord_payout.create(
                    payment_id=payment_id,
                    landlord_id=payment.landlord_id,
                    amount=amount,
                    status=PayoutStatus.PENDING,
                )
            payout_id = payout.id

            self.landlord_payout.update_status(
                payout_id=payout_id, status=PayoutStatus.PROCESSING
            )

            response = self.payout_service.transfer_to_landlord(
                provider=payment.payment_provider,
                payment=payment,
                amount=amount,
                landlord_profile=landlord_profile,
            )
            landlord_response = self.landlord_payout.update_status(
                payout_id=payout_id, status=PayoutStatus.COMPLETED
            )
            payout.provider_reference = response["reference"]
            self.landlord_payout.sync_db_commit()
            if landlord_response.status == PayoutStatus.COMPLETED:
                self.rent_receipt.create_from_payment(payment)
                self.tenant_repo.sync_activate_or_deactivate(
                    tenant_id=payment.tenant_id, is_active=True
                )

        except Exception as e:
            logger.exception("Auto Payout Failed %s", str(e))
            self.landlord_payout.update_status(
                payout_id=payout_id, status=PayoutStatus.FAILED
            )
