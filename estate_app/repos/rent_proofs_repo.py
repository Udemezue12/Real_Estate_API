import uuid
from datetime import datetime

from fastapi import HTTPException
from models.enums import RENT_PAYMENT_STATUS
from models.models import Property, RentPaymentProof, RentReceipt, Tenant
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload


class PaymentProofRepo:
    def __init__(self, db):
        self.db = db

    async def get_by_hash(self, property_id: uuid.UUID, file_hash: str):
        stmt = select(RentPaymentProof).where(
            RentPaymentProof.property_id == property_id,
            RentPaymentProof.file_hash == file_hash,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_listing(self, property_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(RentPaymentProof.id)).where(
                RentPaymentProof.property_id == property_id
            )
        )
        return result.scalar_one()

    async def count_user_uploads_between(
        self,
        user_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> RentPaymentProof:
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)

        if end.tzinfo is not None:
            end = end.replace(tzinfo=None)
        stmt = (
            select(func.count(RentPaymentProof.id))
            .where(RentPaymentProof.created_by_id == user_id)
            .where(RentPaymentProof.uploaded_at >= start)
            .where(RentPaymentProof.uploaded_at < end)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def create(
        self,
        property_id: uuid.UUID,
        tenant_id: uuid.UUID,
        file_url: str,
        file_hash: str,
        public_id: str,
        created_by_id: uuid.UUID,
        status: RENT_PAYMENT_STATUS,
    ) -> RentPaymentProof:
        image = RentPaymentProof(
            file_path=file_url,
            file_hash=file_hash,
            public_id=public_id,
            property_id=property_id,
            created_by_id=created_by_id,
            status=status,
            tenant_id=tenant_id,
        )
        self.db.add(image)
        try:
            await self.db.commit()
            await self.db.refresh(image)
            return image
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_one(self, proof_id: uuid.UUID) -> RentPaymentProof | None:
        result = await self.db.execute(
            select(RentPaymentProof)
            .where(RentPaymentProof.id == proof_id)
            .options(
                selectinload(RentPaymentProof.property).selectinload(Property.owner),
                selectinload(RentPaymentProof.property).selectinload(Property.state),
                selectinload(RentPaymentProof.property).selectinload(Property.lga),
                selectinload(RentPaymentProof.property).selectinload(Property.images),
                selectinload(RentPaymentProof.tenant),
                selectinload(RentPaymentProof.uploaded_by),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self, user_id: uuid.UUID) -> list[RentPaymentProof]:
        result = await self.db.execute(
            select(RentPaymentProof)
            .where(RentPaymentProof.created_by_id == user_id)
            .options(
                selectinload(RentPaymentProof.property),
                selectinload(RentPaymentProof.tenant),
                selectinload(RentPaymentProof.uploaded_by),
                selectinload(RentPaymentProof.property).selectinload(Property.state),
                selectinload(RentPaymentProof.property).selectinload(Property.lga),
                selectinload(RentPaymentProof.property).selectinload(Property.images),
            )
        )
        return result.scalars().all()

    async def get_single(self, user_id: uuid.UUID) -> RentPaymentProof:
        result = await self.db.execute(
            select(RentPaymentProof)
            .where(RentPaymentProof.created_by_id == user_id)
            .options(
                selectinload(RentPaymentProof.property),
                selectinload(RentPaymentProof.tenant),
                selectinload(RentPaymentProof.uploaded_by),
                selectinload(RentPaymentProof.property).selectinload(Property.state),
                selectinload(RentPaymentProof.property).selectinload(Property.lga),
                selectinload(RentPaymentProof.property).selectinload(Property.images),
            )
        )
        return result.scalar_one_or_none()

    async def get_one_by_user(
        self,
        proof_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> RentPaymentProof | None:
        result = await self.db.execute(
            select(RentPaymentProof)
            .where(
                RentPaymentProof.id == proof_id,
                RentPaymentProof.created_by_id == user_id,
            )
            .options(
                selectinload(RentPaymentProof.property),
                selectinload(RentPaymentProof.tenant),
                selectinload(RentPaymentProof.uploaded_by),
                selectinload(RentPaymentProof.property).selectinload(Property.state),
                selectinload(RentPaymentProof.property).selectinload(Property.lga),
                selectinload(RentPaymentProof.property).selectinload(Property.images),
            )
        )
        return result.scalar_one_or_none()

    async def get_one_for_landlord(
        self,
        proof_id: uuid.UUID,
        landlord_id: uuid.UUID,
    ) -> RentPaymentProof | None:
        result = await self.db.execute(
            select(RentPaymentProof)
            .join(RentPaymentProof.property)
            .where(
                RentPaymentProof.id == proof_id,
                or_(
                    Property.owner_id == landlord_id,
                    Property.managed_by_id == landlord_id,
                ),
            )
            .options(
                selectinload(RentPaymentProof.property),
                selectinload(RentPaymentProof.tenant),
                selectinload(RentPaymentProof.uploaded_by),
                selectinload(RentPaymentProof.property).selectinload(Property.state),
                selectinload(RentPaymentProof.property).selectinload(Property.lga),
                selectinload(RentPaymentProof.property).selectinload(Property.images),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_for_landlord(
        self,
        landlord_id: uuid.UUID,
    ) -> list[RentPaymentProof]:
        result = await self.db.execute(
            select(RentPaymentProof)
            .join(RentPaymentProof.property)
            .where(
                or_(
                    Property.owner_id == landlord_id,
                    Property.managed_by_id == landlord_id,
                )
            )
            .options(
                selectinload(RentPaymentProof.property),
                selectinload(RentPaymentProof.tenant),
                selectinload(RentPaymentProof.uploaded_by),
                selectinload(RentPaymentProof.property).selectinload(Property.state),
                selectinload(RentPaymentProof.property).selectinload(Property.lga),
                selectinload(RentPaymentProof.property).selectinload(Property.images),
            )
        )
        return result.scalars().all()

    async def get_all_for_property(
        self,
        property_id: uuid.UUID,
        landlord_id: uuid.UUID,
    ) -> list[RentPaymentProof]:
        result = await self.db.execute(
            select(RentPaymentProof)
            .join(RentPaymentProof.property)
            .where(
                RentPaymentProof.property_id == property_id,
                or_(
                    Property.owner_id == landlord_id,
                    Property.managed_by_id == landlord_id,
                ),
            )
            .options(
                selectinload(RentPaymentProof.property),
                selectinload(RentPaymentProof.tenant),
                selectinload(RentPaymentProof.uploaded_by),
                selectinload(RentPaymentProof.property).selectinload(Property.state),
                selectinload(RentPaymentProof.property).selectinload(Property.lga),
                selectinload(RentPaymentProof.property).selectinload(Property.images),
            )
        )
        return result.scalars().all()

    async def delete_one(self, proof_id: uuid.UUID):
        stmt = (
            delete(RentPaymentProof)
            .where(RentPaymentProof.id == proof_id)
            .returning(RentPaymentProof)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        deleted = result.scalar_one_or_none()
        if not deleted:
            raise HTTPException(status_code=404, detail="File not found")
        return deleted

    async def get_pending_proof(self, proof_id: uuid.UUID) -> RentPaymentProof | None:
        stmt = (
            select(RentPaymentProof)
            .where(
                RentPaymentProof.id == proof_id,
                RentPaymentProof.status == RENT_PAYMENT_STATUS.PENDING,
            )
            .options(
                selectinload(RentPaymentProof.property).selectinload(Property.state),
                selectinload(RentPaymentProof.property).selectinload(Property.lga),
                selectinload(RentPaymentProof.property).selectinload(Property.images),
                selectinload(RentPaymentProof.tenant).selectinload(Tenant.property),
                selectinload(RentPaymentProof.tenant).selectinload(Tenant.matched_user),
                selectinload(RentPaymentProof.uploaded_by),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def mark_paid(self, receipt_id: uuid.UUID) -> RentReceipt:
        try:
            stmt = (
                update(RentPaymentProof)
                .where(RentPaymentProof.rent_receipt_id == receipt_id)
                .values(status=RENT_PAYMENT_STATUS.PAID)
            )
            proofs_paid = await self.db.execute(stmt)
            await self.db.commit()
            return proofs_paid

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def finalize_payment_once(self, receipt_id: uuid.UUID) -> RentReceipt:
        try:
            stmt = (
                update(RentPaymentProof)
                .where(
                    RentPaymentProof.rent_receipt_id == receipt_id,
                    RentPaymentProof.status == RENT_PAYMENT_STATUS.PENDING,
                )
                .values(status=RENT_PAYMENT_STATUS.PAID)
            )
            results = await self.db.execute(stmt)
            await self.db.commit()
            return results.rowcount == 1

        except SQLAlchemyError:
            await self.db.rollback()
            raise
