

from decimal import Decimal

from fintechs.syncFlutterwave import FlutterwaveClient
from fintechs.syncPaystack import PaystackClient
from models.enums import PaymentProvider


class PayoutService:
    def __init__(self):
        self.paystack= PaystackClient()
        self.flutterwave=FlutterwaveClient()
    def transfer_to_landlord(
        self,
        *,
        provider: PaymentProvider,
        amount: Decimal,
        landlord_profile,
        payment,
    ):
        reference = payment.provider_reference

        if provider == PaymentProvider.PAYSTACK:
            return self.paystack.transfer(
                amount=amount,
                recipient_code=landlord_profile.paystack_recipient_code,
                reference=reference,
            )

        if provider == PaymentProvider.FLUTTERWAVE:
            return self.flutterwave.transfer(
                amount=amount,
                account_number=landlord_profile.account_number,
                bank_code=landlord_profile.flutterwave_bank_code,
                reference=reference,
            )

        raise ValueError("Unsupported payout provider")
