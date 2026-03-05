import time

from email_notify.email_service import EmailService
from fintechs.syncFlutterwave import FlutterwaveClient
from fintechs.syncPaystack import PaystackClient
from models.enums import PaymentProvider, PaymentStatus
from repos.payment_transaction_repo import PaymentTransactionRepo
from sms_notify.sms_service import TermiiClient
from tasks.process_payment_transfer_tasks import create_auto_payout_task


class PaymentRetry:
    def __init__(self, db):

        self.paystack = PaystackClient()
        self.flutterwave = FlutterwaveClient()
        self.repo = PaymentTransactionRepo(db)
        self.email_service: EmailService = EmailService()
        self.sms_service: TermiiClient = TermiiClient()

    def run_retry(self, reference: str):
        payment = self.repo.sync_get_reference(reference)

        if not payment:
            return

        if payment.status == PaymentStatus.VERIFIED:
            return
        if payment.status == PaymentStatus.REFUNDED:
            return
        amount = f"₦{payment.amount_received:,.2f}"
        tenant_phoneNumber = payment.tenant_phoneNumber
        landlord_phoneNumber = payment.landlord_phoneNumber
        landlord_email = payment.landlord_email
        tenant_email = payment.tenant_email
        landlord_name = f"{payment.landlord_firstname} {payment.landlord_middlename} {payment.landlord_lastname}"
        tenant_name = f"{payment.tenant_firstname} {payment.tenant_middlename} {payment.tenant_lastname}"

        retries = 3
        base_delay = 5

        for attempt in range(retries):
            try:
                if payment.payment_provider == PaymentProvider.PAYSTACK:
                    data = self.paystack.verify_payment(reference)
                    success = data.get("success") is True
                    if success:
                        transaction_id = str(data["transaction_id"])
                        self.repo.sync_set_transaction_id(
                            payment.id, transaction_id)

                else:
                    data = self.flutterwave.verify_payment(reference)
                    success = data.get("success") is True
                    if success:
                        flw_ref = data["flw_ref"]
                        transaction_id = str(data["transaction_id"])

                        self.repo.sync_set_reference(payment.id, flw_ref)
                        self.repo.sync_set_transaction_id(
                            payment.id, transaction_id)

                if success:
                    self.repo.sync_update_status(
                        payment_id=payment.id,
                        status=PaymentStatus.VERIFIED,
                    )
                    create_auto_payout_task.delay(str(payment.id))

                    if tenant_phoneNumber:
                        self.sms_service.sync_send_tenant_rent_paid_sms(
                            tenant_phoneNumber,
                            amount,
                            tenant_name)

                    if landlord_phoneNumber:

                        self.sms_service.sync_rent_paid_sms(
                            landlord_phoneNumber,
                            amount,
                            landlord_name,
                            tenant_name
                        )

                    self.email_service.sync_send_rent_paid_email(
                        landlord_email,
                        landlord_name,
                        tenant_name,
                        amount,
                    )

                    return

            except Exception as e:
                print(f"Retry attempt failed: {e}")
                pass

            sleep_time = base_delay * (2**attempt)
            time.sleep(sleep_time)

        try:
            if payment.payment_provider == PaymentProvider.PAYSTACK:
                self.paystack.refund(reference)
            elif payment.payment_provider == PaymentProvider.FLUTTERWAVE:
                self.flutterwave.refund_payment(payment.transaction_id)

            self.repo.sync_update_status(
                payment_id=payment.id,
                status=PaymentStatus.REFUNDED,
            )

            if tenant_phoneNumber:
                self.sms_service.sync_send_refund_sms(
                    tenant_phoneNumber,
                    amount,
                    tenant_name,
                )
            if tenant_email:
                self.email_service.sync_send_refund_email(
                    tenant_email,
                    tenant_name,
                    amount,
                )

        except Exception as e:
            print(f"Refund failed: {e}")
            self.repo.sync_update_status(
                payment.id,
                PaymentStatus.FAILED,
            )
