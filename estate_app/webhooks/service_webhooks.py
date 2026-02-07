from fastapi import BackgroundTasks, HTTPException, Request

from celery_worker.celery_app import app as task_app
from core.breaker import CircuitBreaker
from email_notify.email_service import EmailService
from fintech_process_payments.process_payment import ProcessPaymentService
from fintech_verify_signature.verify_signature import FintechsVerifySignature
from fintechs.flutterwave import FlutterwaveClient
from fintechs.paystack import PaystackClient
from models.enums import PaymentProvider, PaymentStatus
from repos.payment_transaction_repo import PaymentTransactionRepo
from repos.rent_payment_repo import RentReceiptRepo
from sms_notify.sms_service import TermiiClient


class PaymentWebhooks:
    def __init__(self, db, request: Request):
        self.request = request
        self.flutterwave = FlutterwaveClient()
        self.paystack = PaystackClient()
        self.breaker: CircuitBreaker = CircuitBreaker()
        self.process_payment_service: ProcessPaymentService = ProcessPaymentService(db)
        self.payment_transaction_repo: PaymentTransactionRepo = PaymentTransactionRepo(
            db
        )
        self.verify_signature: FintechsVerifySignature = FintechsVerifySignature()
        self.email_service: EmailService = EmailService()
        self.sms_service: TermiiClient = TermiiClient()
        self.rent_receipt_repo: RentReceiptRepo = RentReceiptRepo(db)

    async def paystack_webhook(self, background_tasks: BackgroundTasks):
        async def handler():
            raw_body = await self.request.body()

            signature = self.request.headers.get("x-paystack-signature")

            if not self.verify_signature.verify_paystack_signature(signature, raw_body):
                raise HTTPException(401, "Invalid signature")
            payload = await self.request.json()
            if payload["event"] != "charge.success":
                return {"status": "ignored"}
            data = payload["data"]
            reference = payload["data"]["reference"]
            payment = await self.payment_transaction_repo.get_reference(
                reference=reference
            )
            if not payment:
                return {"status": "Unknown Payment"}

            if payment.status == PaymentStatus.VERIFIED:
                return {"status": "already processed"}
            verification = await self.paystack.verify_payment(reference)
            if not verification.get("success"):
                await self.payment_transaction_repo.update_status_provider(
                    payment_id=payment.id,
                    status=PaymentStatus.FAILED,
                    payment_provider=PaymentProvider.NONE_YET,
                )
                raise HTTPException(400, "Failed")

            amount = verification["amount"] / 100
            currency = verification["currency"]

            invoice_id = verification["metadata"]["invoice_id"]
            await self.payment_transaction_repo.update_status_provider(
                payment_id=payment.id,
                status=PaymentStatus.VERIFIED,
                payment_provider=PaymentProvider.PAYSTACK,
            )
            amount = str(payment.amount_received)
            tenant_phoneNumber = payment.tenant_phoneNumber
            landlord_phoneNumber = payment.landlord_phoneNumber
            landlord_email = payment.landlord_email
            landlord_name = f"{payment.landlord_firstname} {payment.landlord_middlename} {payment.landlord_lastname}"
            tenant_name = f"{payment.tenant_firstname} {payment.tenant_middlename} {payment.tenant_lastname}"
            

            background_tasks.add_task(
                self.sms_service.send_tenant_rent_paid_sms,
                tenant_phoneNumber,
                amount,
                tenant_name,
            )
            background_tasks.add_task(
                self.sms_service.rent_paid_sms,
                landlord_phoneNumber,
                amount,
                landlord_name,
                tenant_name,
            )
            background_tasks.add_task(
                self.email_service.send_rent_paid_email,
                landlord_email,
                landlord_name,
                tenant_name,
                amount,
            )
            task_app.send_task("auto_payout_landlord", args=[str(payment.id)])

            return {
                "data": data,
                "status": "ok",
                "amount": amount,
                "currency": currency,
                "invoice_id": invoice_id,
            }

        return await self.breaker.call(handler)

    async def flutterwave_webhook(self, background_tasks: BackgroundTasks):
        async def handler():
            raw_body = await self.request.body()

            signature = self.request.headers.get("verif-hash")
            if not self.verify_signature.verify_flutterwave_signature(
                signature, raw_body
            ):
                raise HTTPException(401, "Invalid signature")
            # client_ip = self.request.headers.get(
            #     "x-forwarded-for", self.request.client.host
            # ).split(",")[0]

            # if not is_allowed_ip(client_ip):
            #     raise HTTPException(403, "Forbidden IP")
            payload = await self.request.json()

            if payload["event"] != "charge.completed":
                return {"status": "ignored"}

            data = payload["data"]
            tx_ref = data["tx_ref"]
            if not tx_ref:
                return {"status": "invalid payload"}
            payment = await self.payment_transaction_repo.get_reference(
                reference=tx_ref
            )
            if not payment:
                return {"status": "Unknown Payment"}
            if payment.status == PaymentStatus.VERIFIED:
                return {"status": "already processed"}

            verification = await self.flutterwave.verify_payment(tx_ref)

            if not verification.get("success"):
                await self.payment_transaction_repo.update_status_provider(
                    payment_id=payment.id,
                    status=PaymentStatus.FAILED,
                    payment_provider=PaymentProvider.NONE_YET,
                )
                raise HTTPException(400, "Failed")
            flw_ref = verification.get("flw_ref")

            if flw_ref:
                await self.payment_transaction_repo.set_reference(payment.id, flw_ref)

            amount = verification["amount"]
            currency = verification["currency"]
            invoice_id = verification["meta"]["invoice_id"]
            await self.payment_transaction_repo.update_status_provider(
                payment_id=payment.id,
                status=PaymentStatus.VERIFIED,
                payment_provider=PaymentProvider.FLUTTERWAVE,
            )
            amount = str(payment.amount_received)
            tenant_phoneNumber = payment.tenant_phoneNumber
            landlord_phoneNumber = payment.landlord_phoneNumber
            landlord_email = payment.landlord_email
            landlord_name = f"{payment.landlord_firstname} {payment.landlord_middlename} {payment.landlord_lastname}"
            tenant_name = f"{payment.tenant_firstname} {payment.tenant_middlename} {payment.tenant_lastname}"

            background_tasks.add_task(
                self.sms_service.send_tenant_rent_paid_sms,
                tenant_phoneNumber,
                amount,
                tenant_name,
            )
            background_tasks.add_task(
                self.sms_service.rent_paid_sms,
                landlord_phoneNumber,
                amount,
                landlord_name,
                tenant_name,
            )
            background_tasks.add_task(
                self.email_service.send_rent_paid_email,
                landlord_email,
                landlord_name,
                tenant_name,
                amount,
            )

            task_app.send_task("auto_payout_landlord", args=[str(payment.id)])

            return {
                "status": "ok",
                "amount": amount,
                "currency": currency,
                "invoice_id": invoice_id,
            }

        return await self.breaker.call(handler)
