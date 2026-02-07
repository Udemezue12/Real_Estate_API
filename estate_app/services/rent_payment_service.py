import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

from celery import chain
from fastapi import BackgroundTasks, HTTPException

from celery_worker.celery_app import app as task_app
from core.breaker import breaker
from core.check_permission import CheckRolePermission
from core.event_publish import publish_event
from core.redis_idempotency import RedisIdempotency
from email_notify.email_service import EmailService
from fintechs.flutterwave import FlutterwaveClient
from fintechs.paystack import PaystackClient
from models.enums import AccountNumberVerificationStatus, PaymentProvider, PaymentStatus
from repos.idempotency_repo import IdempotencyRepo
from repos.payment_transaction_repo import PaymentTransactionRepo
from repos.property_repo import PropertyRepo
from repos.rent_payment_repo import RentReceiptRepo
from repos.tenant_repo import TenantRepo
from sms_notify.sms_service import TermiiClient


class RentPaymentService:
    LOCK_KEY = "rent-payment-process-v2"

    def __init__(self, db):
        self.db = db
        self.rent_receipt_repo: RentReceiptRepo = RentReceiptRepo(db)
        self.repo: PaymentTransactionRepo = PaymentTransactionRepo(db)
        self.tenant_repo: TenantRepo = TenantRepo(db)
        self.property_repo: PropertyRepo = PropertyRepo(db)
        self.paystack = PaystackClient()
        self.flutterwave = FlutterwaveClient()
        self.idem_repo: IdempotencyRepo = IdempotencyRepo(db)
        self.email_service: EmailService = EmailService()
        self.sms_service: TermiiClient = TermiiClient()
        self.idempotency: RedisIdempotency = RedisIdempotency(
            namespace="online_rent_payment"
        )
        self.permission: CheckRolePermission = CheckRolePermission()

    async def payment_options(
        self,
        data,
        gateway_amount,
        current_user,
        payment,
        owner_profile,
    ) -> dict:
        reference = f"PMT-{payment.id.hex}-{uuid.uuid4().hex[:12]}"

        if data.payment_provider == PaymentProvider.PAYSTACK:
            if not owner_profile.paystack_recipient_code:
                raise HTTPException(
                    status_code=400,
                    detail="The paystack account of this property owner is not set up to receive payments.Please select a different payment method or proceed with offline payment and submit proof.",
                )
            paystack_data = await self.paystack.initialize_payment(
                email=current_user.email, amount=gateway_amount, reference=reference
            )
            await self.repo.set_reference(payment.id, reference)
            authorization_url = paystack_data.get(
                "authorization_url"
            ) or paystack_data.get("link")
        elif data.payment_provider == PaymentProvider.FLUTTERWAVE:
            if not owner_profile.flutterwave_bank_code:
                raise HTTPException(
                    status_code=400,
                    detail="The flutterwave account of this property owner is not set up to receive payments.Please select a different payment method or proceed with offline payment and submit proof.",
                )
            flutterwave_data = await self.flutterwave.initialize_payment(
                email=current_user.email, amount=gateway_amount
            )
            tx_ref = str(flutterwave_data["tx_ref"])
            authorization_url = flutterwave_data["checkout_link"]
            await self.repo.set_reference(payment.id, tx_ref)
            reference = tx_ref

        else:
            raise HTTPException(status_code=400, detail="Invalid payment method")

        return {
            "payment_id": str(payment.id),
            "authroization_url": authorization_url,
            "reference": reference,
        }

    async def process_rent_payment(self, current_user, data):
        async def _start():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            tenant = await self.tenant_repo.get_by_user(user_id)

            if not tenant:
                raise HTTPException(
                    status_code=403,
                    detail="Only tenants can pay rents",
                )
            property_id = data.property_id
            tenant_id = tenant.id

            property = await self.property_repo.get_by_id(property_id=property_id)

            if not property:
                raise HTTPException(400, "Tenant is not assigned to this property")
            receipt = await self.rent_receipt_repo.get_unpaid_receipt_for_tenant(
                tenant_id
            )

            if not receipt.fully_paid:
                raise HTTPException(
                    status_code=400,
                    detail="You have an outstanding rent debt,make use of the process_complete_rent_payment button",
                )

            owner_profile = property.owner.profile
            if AccountNumberVerificationStatus.VERIFIED not in (
                owner_profile.paystack_account_verification_status,
                owner_profile.flutterwave_account_verification_status,
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Landlord account is not verified on any payment provider.",
                )

            amount = Decimal(str(tenant.rent_amount))
            payment = await self.repo.create(
                tenant_id=tenant_id,
                property_id=property_id,
                payment_provider=data.payment_provider,
                amount=amount,
                currency=data.currency,
                status=PaymentStatus.PENDING,
                owner_id=property.owner_id,
                landlord_profile_id=property.owner.profile.id,
                tenant_email=current_user.email,
                landlord_email=property.owner.email,
                landlord_firstname=property.owner.first_name,
                landlord_lastname=property.owner.last_name,
                landlord_middlename=property.owner.middle_name,
                tenant_firstname=current_user.first_name,
                tenant_lastname=current_user.last_name,
                tenant_middlename=current_user.middle_name,
                tenant_phoneNumber=current_user.phone_number,
                landlord_phoneNumber=property.owner.phone_number,
                landlord_id=property.owner_id,
            )

            await self.repo.db_commit()
            if not payment:
                raise HTTPException(500, "Payment creation failed")

            gateway_amount = int(tenant.rent_amount * 1)
            return await self.payment_options(
                data=data,
                gateway_amount=gateway_amount,
                current_user=current_user,
                owner_profile=owner_profile,
                payment=payment,
            )

            # return {
            #     "authorization_url": payment_gateway.authorization_url,
            #     "reference": payment_gateway.reference,
            # }

        return await self.idempotency.run_once(
            key=self.LOCK_KEY,
            coro=_start,
            ttl=120,
        )

    async def process_complete_rent_payment(self, current_user, data):
        async def _start():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            tenant = await self.tenant_repo.get_by_user(user_id)
            if not tenant:
                raise HTTPException(
                    status_code=403,
                    detail="Only tenants can pay rents",
                )
            property_id = data.property_id
            tenant_id = tenant.id
            receipt = await self.rent_receipt_repo.get_unpaid_receipt_for_tenant(
                tenant_id
            )

            property = await self.property_repo.get_by_id(property_id=property_id)
            if not property:
                raise HTTPException(400, "Tenant is not assigned to this property")
            if not receipt:
                raise HTTPException(400, "No rent record found")
            if receipt.fully_paid:
                raise HTTPException(status_code=400, detail="No outstanding rent")
            balance = receipt.balance

            owner_profile = property.owner.profile
            if AccountNumberVerificationStatus.VERIFIED not in (
                owner_profile.paystack_account_verification_status,
                owner_profile.flutterwave_account_verification_status,
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Landlord account is not verified on any payment provider.",
                )
            amount = Decimal(str(balance))

            payment = await self.repo.create(
                tenant_id=tenant_id,
                property_id=property_id,
                payment_provider=data.payment_provider,
                amount=amount,
                currency=data.currency,
                status=PaymentStatus.PENDING,
                owner_id=property.owner_id,
                landlord_profile_id=property.owner.profile.id,
                tenant_email=current_user.email,
                landlord_email=property.owner.email,
                landlord_firstname=property.owner.first_name,
                landlord_lastname=property.owner.last_name,
                landlord_middlename=property.owner.middle_name,
                tenant_firstname=current_user.first_name,
                tenant_lastname=current_user.last_name,
                tenant_middlename=current_user.middle_name,
                tenant_phoneNumber=current_user.phone_number,
                landlord_phoneNumber=property.owner.phone_number,
                landlord_id=property.owner_id,
            )

            await self.repo.db_commit()
            if not payment:
                raise HTTPException(500, "Payment creation failed")

            gateway_amount = int(balance * 1)
            return await self.payment_options(
                data=data,
                gateway_amount=gateway_amount,
                current_user=current_user,
                owner_profile=owner_profile,
                payment=payment,
            )

            # return {
            #     "authorization_url": payment_gateway.authorization_url,
            #     "reference": payment_gateway.reference,
            # }

        return await self.idempotency.run_once(
            key=self.LOCK_KEY,
            coro=_start,
            ttl=120,
        )

    async def verify_payment(
        self, reference: str, background_tasks: BackgroundTasks, current_user
    ):
        await self.permission.check_authenticated(current_user=current_user)
        payment = await self.repo.get_reference(reference)

        if not payment:
            raise ValueError("Payment not found")

        success = False
        flw_ref = None

        if payment.payment_provider == PaymentProvider.PAYSTACK:
            data = await self.paystack.verify_payment(reference=reference)
            success = data.get("success") is True

        elif payment.payment_provider == PaymentProvider.FLUTTERWAVE:
            data = await self.flutterwave.verify_payment(reference)
            success = data.get("success") is True
            if success:
                flw_ref = data["flw_ref"]
                await self.repo.set_reference(payment.id, flw_ref)
        else:
            raise HTTPException(404, "No payment provider was found")

        if not success:
            await self.repo.update_status_provider(
                payment_id=payment.id,
                status=PaymentStatus.FAILED,
                payment_provider=PaymentProvider.NONE_YET,
            )
            raise HTTPException(status_code=400, detail="Payment verification failed")
        await self.repo.update_status(payment.id, PaymentStatus.VERIFIED)
        amount = str(payment.amount_received)
        tenant_phoneNumber = payment.tenant_phoneNumber
        landlord_phoneNumber = payment.landlord_phoneNumber
        landlord_email = payment.landlord_email
        landlord_name = f"{payment.landlord_firstname} {payment.landlord_middlename} {payment.landlord_lastname}"
        tenant_name = f"{payment.tenant_firstname} {payment.tenant_middlename} {payment.tenant_lastname}"

        if tenant_phoneNumber:
            background_tasks.add_task(
                self.sms_service.send_tenant_rent_paid_sms,
                tenant_phoneNumber,
                amount,
                tenant_name,
            )
        if landlord_phoneNumber:
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

        chain(
            task_app.signature("auto_payout_landlord", args=[str(payment.id)])
        ).apply_async()

        (
            await publish_event(
                "payment.completed",
                {
                    "payment_id": str(payment.id),
                    "property_id": str(payment.property_id),
                    "user_id": str(payment.tenant_id),
                    "amount": payment.amount_received,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ),
        )

        return {"payment_id": payment.id, "status": "completed"}

    async def refund_payment(self, payment_id: int, current_user):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            payment = await self.repo.get_payment_id(payment_id)
            if not payment:
                raise ValueError("Payment not found")
            if payment.status != PaymentStatus.REFUNDED:
                raise HTTPException(status_code=400, detail="Payment already refunded")
            if payment.status == PaymentStatus.VERIFIED:
                raise HTTPException(
                    status_code=400, detail="Only pending payments can be refunded"
                )

            if payment.payment_provider == PaymentProvider.PAYSTACK:
                await self.paystack.refund(payment.reference)
            else:
                await self.flutterwave.refund_payment(payment.reference)

            await self.repo.update_status(payment.id, PaymentStatus.REFUNDED)

            (
                await publish_event(
                    "payment.refunded",
                    {
                        "payment_id": payment.id,
                        "property_id": payment.property_id,
                        "user_id": payment.tenant_id,
                        "amount": payment.amount_received,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            )

            return {"payment_id": payment_id, "status": "refunded"}

        return await breaker.call(handler)
