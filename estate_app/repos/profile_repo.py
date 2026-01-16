import uuid
from datetime import date, datetime
from typing import Optional

from models.enums import (
    GenderChoices,
    BVNStatus,
    NINVerificationProviders,
    NINVerificationStatus,
    BVNVerificationProviders,
)
from models.models import UserProfile
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload


class UserProfileRepo:
    def __init__(self, db):
        self.db = db

    async def has_profile_picture(self, user_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(UserProfile.profile_pic_path).where(
                UserProfile.user_id == user_id,
                UserProfile.profile_pic_path.isnot(None),
            )
        )
        return result.scalar_one_or_none() is not None

    async def count_user_uploads_between(
        self,
        user_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> UserProfile:
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)

        if end.tzinfo is not None:
            end = end.replace(tzinfo=None)
        stmt = (
            select(func.count(UserProfile.id))
            .where(UserProfile.user_id == user_id)
            .where(UserProfile.profile_pic_uploaded_at >= start)
            .where(UserProfile.profile_pic_uploaded_at < end)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_hash(self, user_id: uuid.UUID, profile_pic_hash: str):
        stmt = select(UserProfile).where(
            UserProfile.user_id == user_id,
            UserProfile.profile_pic_hash == profile_pic_hash,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_hash(
        self,
        profile_id: uuid.UUID,
        user_id: uuid.UUID,
        profile_pic_hash: str,
    ) -> None:
        try:
            stmt = (
                update(UserProfile)
                .where(UserProfile.id == profile_id, UserProfile.user_id == user_id)
                .values(profile_pic_hash=profile_pic_hash)
            )

            await self.db.execute(stmt)
            await self.db.flush()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def create(
        self,
        user_id: uuid.UUID,
        profile_pic_path: str,
        profile_pic_hash: str,
        public_id: str,
        bvn_verified: bool,
        nin_verified: bool,
        date_of_birth: date,
        nin_verified_at: datetime,
        bvn_verified_at: datetime,
        gender: GenderChoices,
        address: str,
        bvn_verification_provider: BVNVerificationProviders,
        nin_verification_provider: NINVerificationProviders,
        occupation: str,
        state_of_birth: str,
        nin_verification_status: NINVerificationStatus,
        bvn_verification_status: BVNStatus,
    ) -> UserProfile:
        try:
            profile = UserProfile(
                user_id=user_id,
                profile_pic_hash=profile_pic_hash,
                public_id=public_id,
               
                profile_pic_path=profile_pic_path,
                date_of_birth=date_of_birth,
                gender=gender,
                address=address,
                occupation=occupation,
                nin_verification_provider=nin_verification_provider,
                bvn_verification_provider=bvn_verification_provider,
                bvn_verified_at=bvn_verified_at,
                nin_verified_at=nin_verified_at,
                nin_verified=nin_verified,
                bvn_verified=bvn_verified,
                state_of_birth=state_of_birth,
                bvn_verification_status=bvn_verification_status,
                nin_verification_status=nin_verification_status,
                nin_verification_error=None,
                bvn_verification_error=None,
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
            return profile
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def mark_nin_verified(
        self,
        profile_id: uuid.UUID,
        nin_verification_provider: NINVerificationProviders,
    ):
        try:
            stmt = await self.db.execute(
                update(UserProfile)
                .where(UserProfile.id == profile_id)
                .values(
                    nin_verified=True,
                    nin_verification_status=NINVerificationStatus.VERIFIED,
                    nin_verified_at=datetime.utcnow(),
                    nin_verification_error=None,
                    nin_verification_provider=nin_verification_provider,
                )
            )
            await self.db.commit()
            await self.db.refresh(stmt)
            return stmt
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def mark_nin_verification_failed(self, profile_id: uuid.UUID, nin_error: str):
        try:
            stmt = await self.db.execute(
                update(UserProfile)
                .where(UserProfile.id == profile_id)
                .values(
                    nin_verified=False,
                    nin_verification_status=NINVerificationStatus.FAILED,
                    nin_verified_at=None,
                    nin_verification_error=nin_error,
                    nin_verification_provider=NINVerificationProviders.NONE_YET,
                )
            )
            await self.db.commit()
            await self.db.refresh(stmt)
            return stmt
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_profile(self, profile_id: uuid.UUID) -> UserProfile:
        result = await self.db.execute(
            select(UserProfile)
            .options(selectinload(UserProfile.user))
            .where(UserProfile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def get_profile_by_user(
        self, user_id: uuid.UUID, profile_id: uuid.UUID
    ) -> UserProfile:
        result = await self.db.execute(
            select(UserProfile)
            .options(selectinload(UserProfile.user))
            .where(UserProfile.user_id == user_id, UserProfile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        *,
        new_profile_pic_path: str | None = None,
        new_profile_pic_hash: str | None = None,
        new_public_id: str | None = None,
        new_date_of_birth: date | None = None,
        new_gender: GenderChoices | None = None,
        new_address: str | None = None,
        new_occupation: str | None = None,
        new_state_of_birth: str | None = None,
    ) -> UserProfile:
        values = {}
        if new_profile_pic_path is not None:
            values["profile_pic_path"] = new_profile_pic_path
        if new_profile_pic_hash is not None:
            values["profile_pic_hash"] = new_profile_pic_hash
        if new_public_id is not None:
            values["public_id"] = new_public_id
        if new_gender is not None:
            values["gender"] = new_gender
        if new_date_of_birth is not None:
            values["date_of_birth"] = new_date_of_birth
        if new_address is not None:
            values["address"] = new_address
        if new_occupation is not None:
            values["occupation"] = new_occupation
        if new_state_of_birth is not None:
            values["state_of_birth"] = new_state_of_birth
        if not values:
            return await self.get_profile_by_user(
                profile_id=profile_id, user_id=user_id
            )
        stmt = (
            update(UserProfile)
            .where(UserProfile.id == profile_id, UserProfile.user_id == user_id)
            .values(**values)
            .returning(UserProfile)
        )

        result = await self.db.execute(stmt)
        updated = result.scalar_one_or_none()
        return updated

    async def delete(self, user_id: uuid.UUID, profile_id: uuid.UUID) -> UserProfile:
        stmt = (
            delete(UserProfile)
            .where(
                UserProfile.id == profile_id,
                UserProfile.user_id == user_id,
            )
            .returning(UserProfile)
        )

        result = await self.db.execute(stmt)
        deleted = result.scalar_one_or_none()
        return deleted

    async def mark_bvn_verified(
        self, profile_id: uuid.UUID, bvn_verification_provider: BVNVerificationProviders
    ):
        await self.db.execute(
            update(UserProfile)
            .where(UserProfile.id == profile_id)
            .values(
                bvn_verified=True,
                bvn_status=BVNStatus.VERIFIED,
                bvn_verified_at=datetime.utcnow(),
                bvn_verification_error=None,
                bvn_verification_provider=bvn_verification_provider,
            )
        )
        await self.db_commit()

    async def mark_bvn_failed(
        self, profile_id: uuid.UUID, bvn_error: str | None = None
    ):
        await self.db.execute(
            update(UserProfile)
            .where(UserProfile.id == profile_id)
            .values(
                bvn_status=BVNStatus.FAILED,
                bvn_verification_error=bvn_error,
                bvn_verification_provider=BVNVerificationProviders.NONE_YET,
                bvn_verified=False,
                bvn_verified_at=None,
            )
        )
        await self.db_commit()

    async def db_commit_and_refresh(self, value):
        try:
            await self.db.commit()
            await self.db.refresh(value)
        except SQLAlchemyError:
            await self.db_rollback()
            raise

    async def db_rollback(self):
        await self.db.rollback()

    async def db_commit(
        self,
    ):
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise
