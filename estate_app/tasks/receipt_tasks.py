import asyncio
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from core.cloudinary_setup import cloudinary_client
from core.get_db import AsyncSessionLocal
from core.pdf_generate import ReceiptGenerator
from core.settings import settings
from security.security_generate import user_generate

from models.enums import PDF_STATUS
from models.models import RentReceipt
from repos.rent_payment_repo import RentReceiptRepo
from services.rent_renewal_service import RentAmountAndRenewalService

logger = logging.getLogger("receipts.pdf")


def create_receipt_task(app):
    class ReceiptTasks(app.Task):
        name = "generate_receipt_pdf"

        autoretry_for = (RuntimeError, ConnectionError)
        retry_backoff = True
        retry_jitter = True
        max_retries = 3
        default_retry_delay = 10

        def _run_async(self, coro):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        async def _generate_and_upload(
            self,
            session: AsyncSession,
            receipt_id: uuid.UUID,
        ):
            repo = RentReceiptRepo(session)
            renew_service = RentAmountAndRenewalService(session)

            receipt = await repo.lock_for_pdf(receipt_id)

            if not receipt:
                raise ValueError("Receipt not found")

            if receipt.pdf_status == PDF_STATUS.READY:
                return

            receipt.pdf_status = PDF_STATUS.GENERATING
            await session.commit()

            receipt = await repo.get_for_pdf(receipt_id)

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

                await session.commit()

                await renew_service.renew_from_receipt(receipt)

            except Exception:
                await session.rollback()
                receipt.pdf_status = PDF_STATUS.FAILED
                await cloudinary_client.safe_delete_cloudinary(
                    public_id=receipt.public_id, resource_type="raw"
                )
                await session.commit()
                raise

            finally:
                if pdf_path and pdf_path.exists():
                    try:
                        pdf_path.unlink()
                    except Exception:
                        pass

        def run(self, receipt_id: str):
            async def _runner():
                async with AsyncSessionLocal() as session:
                    await self._generate_and_upload(session, receipt_id)

            return self._run_async(_runner())

    return ReceiptTasks
