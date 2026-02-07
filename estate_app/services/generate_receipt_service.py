import uuid
from pathlib import Path
from typing import Optional

from core.cloudinary_setup import cloudinary_client
from core.pdf_generate import ReceiptGenerator
from core.settings import settings
from models.enums import PDF_STATUS
from repos.rent_payment_repo import RentReceiptRepo
from security.security_generate import user_generate
from services.rent_renewal_service import RentAmountAndRenewalService


class GenerateReceiptPDF:
    def __init__(self, db):
        
        self.repo = RentReceiptRepo(db)
        self.renew_service = RentAmountAndRenewalService(db)

    async def generate_and_upload(self, receipt_id: uuid.UUID):
        receipt = await self.repo.lock_for_pdf(receipt_id)

        if not receipt:
            raise ValueError("Receipt not found")

        if receipt.pdf_status == PDF_STATUS.READY:
            return

        receipt.pdf_status = PDF_STATUS.GENERATING
        await self.repo.db_commit()

        receipt = await self.repo.get_for_pdf(receipt_id)

        if not receipt:
            raise ValueError("Receipt disappeared after lock")

        pdf_path: Optional[Path] = None

        try:
            if not settings.SECRET_KEY:
                raise ValueError("SECRET_KEY is not configured")
            if not receipt.barcode_reference:
                receipt.barcode_reference = await user_generate.hmac_sha256(
                    value=f"{receipt.id}:{receipt.amount}",
                    secret=settings.SECRET_KEY,
                )
            pdf_path = ReceiptGenerator.generate_pdf(receipt)

            upload_result = await cloudinary_client.upload_pdf_with_signature(
                pdf_path,
                public_id=receipt.public_id,
                folder="receipts",
            )

            receipt.public_id = upload_result["public_id"]

            receipt.pdf_status = PDF_STATUS.READY
            receipt.receipt_path = upload_result["secure_url"]

            await self.repo.db_commit()

            await self.renew_service.renew_from_receipt(receipt)

        except Exception:
            await self.repo.db_rollback()
            receipt.pdf_status = PDF_STATUS.FAILED
            await cloudinary_client.safe_delete_cloudinary(
                public_id=receipt.public_id, resource_type="raw"
            )
            await self.repo.db_commit()
            raise

        finally:
            if pdf_path and pdf_path.exists():
                try:
                    pdf_path.unlink()
                except Exception:
                    pass
