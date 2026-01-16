import asyncio
import uuid

from core.breaker import breaker
from core.cache import cache
from core.cloudinary_setup import CloudinaryClient
from core.event_publish import publish_event
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from core.pdf_generate import ReceiptGenerator
from core.redis_idempotency import RedisIdempotency
from core.threads import run_in_thread
from fastapi import HTTPException
from fire_and_forget.rent_receipt import AsyncioRentReceipt
from models.enums import PDF_STATUS, RENT_PAYMENT_STATUS, RentCycle
from models.models import RentReceipt
from policy.rent_proof_policy import ModelPolicy
from repos.idempotency_repo import IdempotencyRepo
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
    def __init__(self, db):
        self.repo: RentReceiptRepo = RentReceiptRepo(db)
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

    async def mark_as_paid(self, current_user, data, proof_id: uuid.UUID, idem_key=str):
        user_id = current_user.id

        proof = await self.proof_repo.get_pending_proof(proof_id)

        if not proof:
            raise ValueError("Payment proof not found or already processed")
        tenant = proof.tenant
        if not await ModelPolicy.can_mark_payment(tenant, user_id):
            raise PermissionError("You are not allowed to mark this payment")
        existing_idem = await self.idem_repo.get(key=idem_key, user_id=current_user.id)
        if existing_idem and existing_idem.response:
            return existing_idem.response
        await self.idem_repo.save(idem_key, current_user.id, "MARK_AS_PAID/receipts")
        if proof.rent_receipt_id:
            return {"message": "Already paid", "receipt_id": proof.rent_receipt_id}

        months = RENT_CYCLE_TO_MONTHS.get(tenant.rent_cycle)
        if not months:
            raise RuntimeError("Unsupported rent cycle")
        if tenant.rent_expiry_date:
            period_start = tenant.rent_expiry_date
        else:
            period_start = tenant.rent_start_date

        receipt = RentReceipt(
            tenant_id=tenant.id,
            property_id=tenant.property_id,
            landlord_id=user_id,
            amount=data.rent_amount,
            month_paid_for=period_start.month,
            year_paid_for=period_start.year,
            rent_duration_months=months,
            public_id=await user_generate.generate_secure_public_id(prefix="receipt"),
            reference_number=f"HMT-{uuid.uuid4().hex[:40]}",
        )

        receipt = await self.repo.create(receipt=receipt)
        if not receipt.id:
            raise RuntimeError("Receipt ID not generated")
        proof.rent_receipt = receipt
        proof.rent_receipt_id = receipt.id
        proof.status = RENT_PAYMENT_STATUS.PAID
        await self.repo.db_commit_and_refresh(receipt)

        response = {
            "message": "Payment marked as paid",
            "receipt_id": str(receipt.id),
            "reference_number": receipt.reference_number,
        }
        asyncio.create_task(
            self.fire_and_forget.mark_as_paid(
                receipt=receipt,
                tenant=tenant,
            )
        )
        await self.idem_repo.store_response(idem_key, response, current_user.id)

        return response

    async def download_receipt(self, current_user, receipt_id: uuid.UUID):
        async def handler():
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
            tenant = await self.tenant_repo.get_by_matched_id(
                matched_user_id=current_user.id
            )
            if not tenant:
                raise HTTPException(400, "Not Permitted")
            receipt = await self.repo.verify_receipt(reference=reference)
            if not receipt:
                raise HTTPException(404, "Receipt not found")
            result = PaymentVerificationResult(
                receipt_id=receipt.id,
                amount=receipt.amount,
                month_paid_for=receipt.month_paid_for,
                year_paid_for=receipt.year_paid_for,
                tenant_name=f"{tenant.first_name} {tenant.last_name}",
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
            if not receipt:
                raise HTTPException(404, "Not Found")
            await self.repo.normal_delete(
                user_id=current_user.id, receipt_id=receipt_id
            )
            await self.cloudinary.delete_image(
                public_id=receipt.public_id, resource_type=resource_type
            )

            asyncio.create_task(
                publish_event(
                    "rent_receipts.deleted",
                    {
                        "receipt_id": str(receipt_id),
                    },
                )
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
