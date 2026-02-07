import uuid
from typing import Optional

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import aliased, selectinload

from models.enums import PDF_STATUS
from models.models import Property, RentReceipt, Tenant


class RentReceiptRepo:
    def __init__(self, db):
        self.db = db

    async def create(self, receipt: RentReceipt) -> RentReceipt:
        # self.db.add(receipt)
        return await self.db_add_and_flush(receipt)

    async def update(self, receipt: RentReceipt) -> RentReceipt:
        # self.db.add(receipt)
        return await self._commit_and_refresh(receipt)

    async def mark_pdf_generating(self, receipt: RentReceipt) -> RentReceipt | None:
        receipt.pdf_status = PDF_STATUS.GENERATING
        self.db.add(receipt)
        return await self._commit_and_refresh(receipt)

    async def mark_pdf_ready(
        self, receipt: RentReceipt, pdf_path: str
    ) -> RentReceipt | None:
        receipt.pdf_status = PDF_STATUS.READY
        receipt.receipt_path = pdf_path
        self.db.add(receipt)
        return await self._commit_and_refresh(receipt)

    async def mark_pdf_failed(self, receipt: RentReceipt) -> RentReceipt | None:
        receipt.pdf_status = PDF_STATUS.FAILED
        self.db.add(receipt)
        return await self._commit_and_refresh(receipt)

    async def lock_for_pdf(self, receipt_id: uuid.UUID) -> Optional[RentReceipt]:
        stmt = select(RentReceipt).where(RentReceipt.id == receipt_id).with_for_update()

        result = await self.db.execute(stmt)
        receipt: RentReceipt | None = result.scalar_one_or_none()

        if not receipt:
            return None

        if receipt.pdf_status == PDF_STATUS.READY:
            return receipt

        receipt.pdf_status = PDF_STATUS.GENERATING
        await self.db_commit_and_refresh(receipt)

        return receipt

    async def get_for_pdf(self, receipt_id: uuid.UUID) -> Optional[RentReceipt]:
        stmt = (
            select(RentReceipt)
            .where(RentReceipt.id == receipt_id)
            .options(
                selectinload(RentReceipt.property).selectinload(Property.state),
                selectinload(RentReceipt.property).selectinload(Property.lga),
                selectinload(RentReceipt.property).selectinload(Property.managed_by),
                selectinload(RentReceipt.property).selectinload(Property.owner),
                selectinload(RentReceipt.tenant).selectinload(Tenant.property),
                selectinload(RentReceipt.landlord),
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _commit_and_refresh(self, receipt: RentReceipt) -> RentReceipt:
        try:
            await self.db.commit()
            await self.db.refresh(receipt)
            return receipt
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def verify_receipt(self, reference: str) -> RentReceipt | None:
        stmt = (
            select(RentReceipt)
            .options(
                selectinload(RentReceipt.payment_proof),
                selectinload(RentReceipt.tenant).selectinload(Tenant.matched_user),
                selectinload(RentReceipt.landlord),
                selectinload(RentReceipt.property).selectinload(Property.owner),
                selectinload(RentReceipt.property).selectinload(Property.state),
                selectinload(RentReceipt.property).selectinload(Property.lga),
                selectinload(RentReceipt.property).selectinload(Property.images),
            )
            .where(RentReceipt.reference_number == reference)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def download_receipt(
        self, receipt_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> RentReceipt:
        receipt = (
            select(RentReceipt)
            .where(RentReceipt.id == receipt_id, RentReceipt.tenant_id == tenant_id)
            .options(
                selectinload(RentReceipt.payment_proof),
                selectinload(RentReceipt.tenant),
                selectinload(RentReceipt.landlord),
                selectinload(RentReceipt.property).selectinload(Property.owner),
                selectinload(RentReceipt.property).selectinload(Property.state),
                selectinload(RentReceipt.property).selectinload(Property.lga),
                selectinload(RentReceipt.property).selectinload(Property.images),
            )
        )
        result = await self.db.execute(receipt)
        return result.scalar_one_or_none()

    async def get_tenant_receipt(
        self, receipt_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> RentReceipt | None:
        stmt = (
            select(RentReceipt)
            .where(
                RentReceipt.id == receipt_id,
                RentReceipt.tenant_id == tenant_id,
                # RentReceipt.property_id == property_id,
            )
            .options(
                selectinload(RentReceipt.payment_proof),
                selectinload(RentReceipt.tenant),
                selectinload(RentReceipt.landlord),
                selectinload(RentReceipt.property).selectinload(Property.owner),
                selectinload(RentReceipt.property).selectinload(Property.state),
                selectinload(RentReceipt.property).selectinload(Property.lga),
                selectinload(RentReceipt.property).selectinload(Property.images),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tenant_receipts_for_property(
        self,
        tenant_id: uuid.UUID,
        property_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> list[RentReceipt]:
        stmt = (
            select(RentReceipt)
            .options(
                selectinload(RentReceipt.payment_proof),
                selectinload(RentReceipt.tenant),
                selectinload(RentReceipt.landlord),
                selectinload(RentReceipt.property).selectinload(Property.owner),
                selectinload(RentReceipt.property).selectinload(Property.state),
                selectinload(RentReceipt.property).selectinload(Property.lga),
                selectinload(RentReceipt.property).selectinload(Property.images),
            )
            .where(
                RentReceipt.tenant_id == tenant_id,
                RentReceipt.property_id == property_id,
            )
            .order_by(RentReceipt.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_property_receipts(
        self, property_id: uuid.UUID, page: int = 1, per_page: int = 20
    ) -> list[RentReceipt]:
        stmt = (
            select(RentReceipt)
            .options(
                selectinload(RentReceipt.payment_proof),
                selectinload(RentReceipt.tenant),
                selectinload(RentReceipt.landlord),
                selectinload(RentReceipt.property).selectinload(Property.owner),
                selectinload(RentReceipt.property).selectinload(Property.state),
                selectinload(RentReceipt.property).selectinload(Property.lga),
                selectinload(RentReceipt.property).selectinload(Property.images),
            )
            .where(
                RentReceipt.property_id == property_id,
            )
            .order_by(RentReceipt.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_receipt_for_property_owner_or_manager(
        self, receipt_id: uuid.UUID, property_id: uuid.UUID
    ) -> RentReceipt | None:
        stmt = (
            select(RentReceipt)
            .options(
                selectinload(RentReceipt.payment_proof),
                selectinload(RentReceipt.tenant),
                selectinload(RentReceipt.landlord),
                selectinload(RentReceipt.property).selectinload(Property.owner),
                selectinload(RentReceipt.property).selectinload(Property.state),
                selectinload(RentReceipt.property).selectinload(Property.lga),
                selectinload(RentReceipt.property).selectinload(Property.images),
            )
            .join(Property, Property.id == RentReceipt.property_id)
            .where(
                RentReceipt.id == receipt_id,
                Property.id == property_id,
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_reference(self, reference: str) -> RentReceipt | None:
        stmt = (
            select(RentReceipt)
            .where(RentReceipt.reference_number == reference)
            .options(
                selectinload(RentReceipt.payment_proof),
                selectinload(RentReceipt.tenant),
                selectinload(RentReceipt.landlord),
                selectinload(RentReceipt.property).selectinload(Property.owner),
                selectinload(RentReceipt.property).selectinload(Property.state),
                selectinload(RentReceipt.property).selectinload(Property.lga),
                selectinload(RentReceipt.property).selectinload(Property.images),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_receipt_id(self, receipt_id: uuid.UUID) -> RentReceipt:
        stmt = select(RentReceipt).where(RentReceipt.id == receipt_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, receipt_id: uuid.UUID, user_id: uuid.UUID) -> RentReceipt:
        TenantAlias = aliased(Tenant)

        stmt = (
            delete(RentReceipt)
            .where(
                RentReceipt.id == receipt_id,
                or_(
                    RentReceipt.landlord_id == user_id,
                    RentReceipt.tenant_id.in_(
                        select(TenantAlias.id).where(
                            TenantAlias.matched_user_id == user_id
                        )
                    ),
                ),
            )
            .returning(RentReceipt)
        )

        try:
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.scalar_one_or_none()

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def normal_delete(self, receipt_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = delete(RentReceipt).where(
            RentReceipt.id == receipt_id, RentReceipt.landlord_id == user_id
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def db_add_and_flush(self, receipt: RentReceipt) -> RentReceipt:
        try:
            self.db.add(receipt)
            await self.db.flush()
            return receipt
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def db_commit(self):
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def db_rollback(self):
        await self.db.rollback()
        

    async def db_commit_and_refresh(self, value):
        try:
            await self.db.commit()
            await self.db.refresh(value)
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_unpaid_receipt_for_tenant(
        self, tenant_id: uuid.UUID
    ) -> RentReceipt | None:
        result = await self.db.execute(
            select(RentReceipt)
            .where(RentReceipt.tenant_id == tenant_id, RentReceipt.fully_paid == False)
            .order_by(RentReceipt.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_fully_paid(self, receipt_id: uuid.UUID, fully_paid: bool):
        stmt = (
            update(RentReceipt)
            .where(RentReceipt.id == receipt_id)
            .values(fully_paid=fully_paid)
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise
