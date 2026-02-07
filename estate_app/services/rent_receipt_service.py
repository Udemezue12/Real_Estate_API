import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException

from core.breaker import breaker
from core.cache import cache
from core.check_permission import CheckRolePermission
from core.cloudinary_setup import CloudinaryClient
from core.event_publish import publish_event
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from core.pdf_generate import ReceiptGenerator
from core.redis_idempotency import RedisIdempotency
from core.threads import run_in_thread
from fire_and_forget.rent_receipt import AsyncioRentReceipt
from models.enums import PDF_STATUS, RENT_PAYMENT_STATUS, RentCycle
from models.models import RentReceipt, Tenant
from policy.rent_proof_policy import ModelPolicy
from repos.idempotency_repo import IdempotencyRepo
from repos.payment_transaction_repo import PaymentTransactionRepo
from repos.property_repo import PropertyRepo
from repos.rent_payment_repo import RentReceiptRepo
from repos.rent_proofs_repo import PaymentProofRepo
from repos.tenant_repo import TenantRepo
from schemas.schema import PaymentVerificationResult, RentReceiptBaseOut
from security.security_generate import user_generate
from services.rent_renewal_service import RentAmountAndRenewalService

RENT_CYCLE_TO_MONTHS = {
    RentCycle.MONTHLY: 1,
    RentCycle.QUARTERLY: 3,
    RentCycle.YEARLY: 12,
}


class RentReceiptService:
    LOCK_KEY = "rent-receipt-service-lock-v2"
    CREATE_LOCK_KEY = "create-from-rent-receipt-service-lock-v2"

    def __init__(self, db):
        self.repo: RentReceiptRepo = RentReceiptRepo(db)
        self.payment_repo: PaymentTransactionRepo = PaymentTransactionRepo(db)
        self.tenant_repo: TenantRepo = TenantRepo(db)
        self.proof_repo: PaymentProofRepo = PaymentProofRepo(db)
        self.property_repo: PropertyRepo = PropertyRepo(db)
        self.idempotency: RedisIdempotency = RedisIdempotency()
        self.tenant_repo: TenantRepo = TenantRepo(db)
        self.renewal_repo: RentReceiptService = RentAmountAndRenewalService(db)
        self.policy: ModelPolicy = ModelPolicy()
        self.cloudinary: CloudinaryClient = CloudinaryClient()
        self.paginate: PaginatePage = PaginatePage()
        self.mapper: ORMMapper = ORMMapper()
        self.idem_repo: IdempotencyRepo = IdempotencyRepo(db)
        self.fire_and_forget: AsyncioRentReceipt = AsyncioRentReceipt()
        self.idempotency: RedisIdempotency = RedisIdempotency(
            namespace="rent_receipt_service"
        )
        self.permission: CheckRolePermission = CheckRolePermission()

    def determine_payment_context(
        self,
        *,
        receipt: RentReceipt,
        tenant: Tenant,
        amount_received: Decimal,
    ) -> str:
        if receipt.amount_paid == 0:
            if amount_received < tenant.rent_amount:
                return "HALF_RENT"

            return "FULL_RENT"

        if receipt.remaining_balance > 0:
            return "OUTSTANDING_BALANCE"

        return "FULL_RENT"

    async def generate_receipt_pdf(self, receipt):
        await self.repo.mark_pdf_generating(receipt)

        try:
            pdf_path = await run_in_thread(
                ReceiptGenerator.generate_pdf,
                receipt,
            )

            await self.repo.mark_pdf_ready(
                receipt=receipt,
                pdf_path=str(pdf_path),
            )

            return pdf_path

        except Exception:
            await self.repo.mark_pdf_failed(receipt)
            raise

    async def create_from_payment(self, payment):
        async def _start():
            tenant = await self.tenant_repo.get_by_id(payment.tenant_id)
            existing_receipt = await self.repo.get_unpaid_receipt_for_tenant(
                payment.tenant_id
            )
            get_payment_context = self.determine_payment_context(
                amount_received=Decimal(str(payment.amount_received)),
                receipt=existing_receipt,
                tenant=tenant,
            )

            if not tenant:
                raise HTTPException(404, "Tenant not found")

            existing = await self.payment_repo.get_payment_id(payment.id)
            if existing:
                return existing
            months = RENT_CYCLE_TO_MONTHS.get(tenant.rent_cycle)
            if not months:
                raise RuntimeError("Unsupported rent cycle")
            if tenant.rent_expiry_date:
                period_start = tenant.rent_expiry_date
            else:
                period_start = tenant.rent_start_date
            if existing_receipt:
                existing_receipt.amount_paid += payment.amount_received
                existing_receipt.fully_paid = (
                    existing_receipt.amount_paid >= existing_receipt.expected_amount
                )
                existing_receipt.remaining_balance = {
                    existing_receipt.amount_paid - existing_receipt.expected_amount
                }
                existing_receipt.payment_context = get_payment_context
                existing_receipt.payment_id = payment.id

                await self.repo.db_commit_and_refresh(existing_receipt)

                receipt = existing_receipt
                receipt_created = existing_receipt
            else:
                receipt = RentReceipt(
                    tenant_id=tenant.id,
                    property_id=payment.property_id,
                    landlord_id=payment.landlord_id,
                    expected_amount=tenant.rent_amount,
                    amount_paid=Decimal(str(payment.amount_received)),
                    month_paid_for=period_start.month,
                    year_paid_for=period_start.year,
                    rent_duration_months=months,
                    payment_id=payment.id,
                    public_id=await user_generate.generate_secure_public_id(
                        prefix="receipt"
                    ),
                    reference_number=f"HMT-{uuid.uuid4().hex[:40]}",
                    fully_paid=True,
                    payment_context="FULL_RENT",
                    balance=0,
                )
                if not receipt.id:
                    raise HTTPException(404, "Not found")

                receipt_created = await self.repo.create(receipt=receipt)
                await self.repo.db_commit_and_refresh(receipt_created)

            tenant_email = payment.tenant_email
            landlord_name = f"{payment.landlord_firstname} {payment.landlord_middlename} {payment.landlord_lastname}"
            tenant_name = f"{payment.tenant_firstname} {payment.tenant_middlename} {payment.tenant_lastname}"
            await self.fire_and_forget.mark_paid(
                receipt=receipt_created,
                tenant=tenant,
                email=tenant_email,
                landlord_name=landlord_name,
                tenant_name=tenant_name,
            )

            return {
                "receipt_id": str(receipt.id),
                "fully_paid": receipt.fully_paid,
                "amount_paid": str(receipt.amount_paid),
                "reference_number": receipt.reference_number,
                "balance": str(receipt.expected_amount - receipt.amount_paid),
            }

        return await self.idempotency.run_once(
            key=self.CREATE_LOCK_KEY,
            coro=_start,
            ttl=120,
        )

    async def mark_as_paid(self, current_user, proof_id: uuid.UUID):
        async def _start():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)

            proof = await self.proof_repo.get_pending_proof(proof_id)

            if not proof:
                raise ValueError("Payment proof not found or already processed")
            tenant = proof.tenant
            tenant_id = proof.tenant_id

            if not await ModelPolicy.can_mark_payment(tenant, user_id):
                raise PermissionError("You are not allowed to mark this payment")

            if proof.rent_receipt_id:
                return {"message": "Already paid", "receipt_id": proof.rent_receipt_id}

            months = RENT_CYCLE_TO_MONTHS.get(tenant.rent_cycle)
            if not months:
                raise RuntimeError("Unsupported rent cycle")
            if tenant.rent_expiry_date:
                period_start = tenant.rent_expiry_date
            else:
                period_start = tenant.rent_start_date
            receipt = await self.repo.get_unpaid_receipt_for_tenant(tenant_id)
            if not receipt:
                receipt = RentReceipt(
                    tenant_id=tenant.id,
                    property_id=tenant.property_id,
                    landlord_id=user_id,
                    amount_paid=0,
                    expected_amount=tenant.rent_amount,
                    month_paid_for=period_start.month,
                    year_paid_for=period_start.year,
                    rent_duration_months=months,
                    fully_paid=False,
                    public_id=await user_generate.generate_secure_public_id(
                        prefix="receipt"
                    ),
                    reference_number=f"HMT-{uuid.uuid4().hex[:40]}",
                )
                receipt = await self.repo.create(receipt=receipt)
            payment_context = self.determine_payment_context(
                receipt=receipt, amount_received=proof.amount_paid, tenant=tenant
            )

            receipt.amount_paid += proof.amount_paid
            receipt.fully_paid = receipt.amount_paid >= receipt.expected_amount
            receipt.payment_context = payment_context
            receipt.remaining_balance = receipt.expected_amount - receipt.amount_paid
            proof.rent_receipt = receipt
            proof.rent_receipt_id = receipt.id
            proof.status = RENT_PAYMENT_STATUS.PAID
            await self.tenant_repo.activate_or_deactivate(
                tenant_id=tenant_id, is_active=True
            )
            await self.repo.db_commit_and_refresh(receipt)

            await self.fire_and_forget.mark_as_paid(
                receipt=receipt,
                tenant=tenant,
            )

            return {
                "message": "Payment proof approved",
                "receipt_id": str(receipt.id),
                "fully_paid": receipt.fully_paid,
                "amount_paid": str(receipt.amount_paid),
                "reference_number": receipt.reference_number,
                "balance": str(receipt.expected_amount - receipt.amount_paid),
            }

        return await self.idempotency.run_once(
            key=self.LOCK_KEY,
            coro=_start,
            ttl=120,
        )

    async def reject_proof(self, current_user, proof_id: uuid.UUID, data):
        async def _start():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)

            proof = await self.proof_repo.get_pending_proof(proof_id)
            if not proof:
                raise HTTPException(404, "Payment proof not found or already processed")

            tenant = proof.tenant

            if not await ModelPolicy.can_mark_payment(tenant, user_id):
                raise HTTPException(403, "You are not allowed to reject this payment")

            proof.status = RENT_PAYMENT_STATUS.REJECTED
            proof.rejection_reason = data.reason
            proof.reviewed_by_id = user_id
            proof.reviewed_at = datetime.utcnow()

            await self.repo.db_commit_and_refresh(proof)

            # Notify tenant
            # await self.fire_and_forget.payment_proof_rejected(
            #     tenant=tenant,
            #     reason=reason,
            # )

            return {
                "message": "Payment proof rejected",
                "proof_id": str(proof.id),
                "reason": data.reason,
            }

        return await self.idempotency.run_once(
            key=f"reject-proof-{proof_id}",
            coro=_start,
            ttl=120,
        )

    async def download_receipt(self, current_user, receipt_id: uuid.UUID):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            tenant = await self.tenant_repo.get_by_matched_id(
                matched_user_id=current_user.id
            )
            if not tenant:
                raise HTTPException(400, "Not Permitted")
            tenant_id = tenant.id

            receipt = await self.repo.download_receipt(
                receipt_id=receipt_id, tenant_id=tenant_id
            )
            if not receipt or not receipt.public_id:
                raise HTTPException(404, "Receipt not found")
            if receipt.pdf_status != PDF_STATUS.READY:
                raise HTTPException(
                    409,
                    "Receipt PDF is still being generated. Please try again shortly.",
                )

            return {
                "download_url": receipt.receipt_path,
                "message": "Use the download_url to download the receipt PDF",
            }

        return await breaker.call(handler)

    async def verify_receipt(self, reference: str, current_user) -> RentReceipt | None:
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)

            receipt = await self.repo.verify_receipt(reference=reference)
            if not receipt:
                raise HTTPException(404, "Receipt not found")
            result = PaymentVerificationResult(
                receipt_id=receipt.id,
                amount=receipt.amount,
                month_paid_for=receipt.month_paid_for,
                year_paid_for=receipt.year_paid_for,
                tenant_name=f"{receipt.tenant.first_name}{receipt.tenant.last_name}",
                property_id=receipt.property_id,
            )
            return {
                "receipt_id": str(result.receipt_id),
                "status": "Paid",
                "amount": result.amount,
                "month_paid_for": result.month_paid_for,
                "year_paid_for": result.year_paid_for,
                "tenant_name": f"{result.tenant_name}",
                "property_id": str(result.property_id),
            }

        return await breaker.call(handler)

    async def get_tenant_receipt(
        self,
        current_user,
        receipt_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)

            # if not tenant:
            #     raise HTTPException(403,"Not permitted")
            cache_key = f"tenant:{tenant_id}:receipt:{receipt_id}:property"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.one(cached, RentReceiptBaseOut)

            receipt = await self.repo.get_tenant_receipt(
                receipt_id=receipt_id,
                tenant_id=tenant_id,
            )

            if not receipt:
                raise HTTPException(404, "Receipt not found")

            receipt_dict = self.mapper.one(receipt, RentReceiptBaseOut)
            await cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(receipt_dict),
                ttl=300,
            )
            return receipt_dict

        return await breaker.call(handler)

    async def get_tenant_receipts_for_property(
        self, current_user, property_id: uuid.UUID, page: int = 1, per_page: int = 20
    ):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            tenant = await self.tenant_repo.get_by_matched_id(matched_user_id=user_id)
            cache_key = f"tenant:{tenant.id}:receipts:property:{property_id}:page:{page}:per_page:{per_page}"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.many(cached, RentReceiptBaseOut)

            if not tenant:
                raise HTTPException(400, "Not permitted")

            receipts = await self.repo.get_tenant_receipts_for_property(
                tenant_id=tenant.id,
                property_id=property_id,
            )
            receipts_list = self.mapper.many(receipts, RentReceiptBaseOut)
            paginated_receipts = self.paginate.paginate(receipts_list, page, per_page)
            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_receipts),
                ttl=300,
            )
            return paginated_receipts

        return await breaker.call(handler)

    async def get_property_receipts(
        self, current_user, property_id: uuid.UUID, page: int = 1, per_page: int = 20
    ):
        async def handler():
            await self.permission.check_authenticated(current_user=current_user)
            property = await self.property_repo.get_property_with_relations(
                property_id=property_id
            )
            property_policy = await self.policy.can_access_property(
                property=property, user_id=current_user.id
            )
            if not property_policy:
                raise HTTPException(403, "Not permitted")
            cache_key = f"property:{property_id}:receipts"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.many(cached, RentReceiptBaseOut)

            receipts = await self.repo.get_property_receipts(property_id)
            receipts_list = self.mapper.many(receipts, RentReceiptBaseOut)
            paginated_receipts = self.paginate.paginate(receipts_list, page, per_page)

            await cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_receipts),
                ttl=300,
            )
            return paginated_receipts

        return await breaker.call(handler)

    async def get_receipt_for_property_owner_or_manager(
        self,
        current_user,
        receipt_id: uuid.UUID,
        property_id: uuid.UUID,
    ):
        async def handler():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            property = await self.property_repo.get_property_with_relations(
                property_id=property_id
            )
            property_policy = await self.policy.can_access_property(
                property=property,
                user_id=user_id,
            )
            if not property_policy:
                raise HTTPException(403, "Not permitted")
            cache_key = f"property:{property_id}:receipt:{receipt_id}"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.one(cached, RentReceiptBaseOut)

            receipt = await self.repo.get_receipt_for_property_owner_or_manager(
                receipt_id=receipt_id,
                property_id=property_id,
            )

            if not receipt:
                raise HTTPException(404, "Receipt not found")
            receipt_dict = self.mapper.one(receipt, RentReceiptBaseOut)
            await cache.set_json(
                cache_key,
                self.paginate.get_single_json_dumps(receipt_dict),
                ttl=300,
            )

            return receipt_dict

        return await breaker.call(handler)

    async def delete(
        self, current_user, receipt_id: uuid.UUID, resource_type: str = "raw"
    ):
        async def handler():
            receipt = await self.repo.get_receipt_id(receipt_id=receipt_id)
            await self.permission.check_authenticated(current_user=current_user)
            if not receipt:
                raise HTTPException(404, "Not Found")
            await self.cloudinary.delete_image(
                public_id=receipt.public_id, resource_type=resource_type
            )
            await self.repo.normal_delete(
                user_id=current_user.id, receipt_id=receipt_id
            )

            await publish_event(
                "rent_receipts.deleted",
                {
                    "receipt_id": str(receipt_id),
                },
            )

            return {"id": str(receipt_id), "message": "Deleted"}

        return await breaker.call(handler)


# @router.get("/rent-receipts/{receipt_id}/barcode")
# async def get_barcode(receipt_id: UUID, db=Depends(get_db)):
#     receipt = await db.get(RentReceipt, receipt_id)
#     return FileResponse(
#         f"media/receipts/{receipt.barcode_reference}.png",
#         media_type="image/png",
#     )
