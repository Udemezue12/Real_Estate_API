import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

from core.breaker import breaker
from core.cache import cache
from core.cloudinary_setup import CloudinaryClient
from core.file_hash import ComputeFileHash
from core.hash_and_update import AsyncioHashAndUpdate
from core.mapper import ORMMapper
from core.name_matcher import NameMatcher
from core.paginate import PaginatePage
from core.sensitive_hash import SensitiveHash
from fastapi import HTTPException
from fire_and_forget.profile import AsyncioUserProfile
from models.enums import BVNStatus, GenderChoices, NINVerificationStatus
from repos.idempotency_repo import IdempotencyRepo
from repos.profile_repo import UserProfileRepo
from schemas.schema import UserProfileSchemaOut
from security.security_generate import UserGenerate

MAX_DAILY_UPLOADS = 1


class UserProfileService:
    def __init__(self, db):
        self.mapper: ORMMapper = ORMMapper()

        self.repo: UserProfileRepo = UserProfileRepo(db)
        self.idem_repo: IdempotencyRepo = IdempotencyRepo(db)
        self.update_hash = AsyncioHashAndUpdate()
        self.cloudinary: CloudinaryClient = CloudinaryClient()
        self.name_matcher: NameMatcher = NameMatcher()
        self.paginate: PaginatePage = PaginatePage()
        self.sensitive_hash: SensitiveHash = SensitiveHash()
        self.generate: UserGenerate = UserGenerate()
        self.compute: ComputeFileHash = ComputeFileHash()
        self.fire_and_forget: AsyncioUserProfile = AsyncioUserProfile()

    async def enforce_daily_quota(self, user_id: uuid.UUID):
        today_start = (
            datetime.now(timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .replace(tzinfo=None)
        )
        tomorrow = today_start + timedelta(days=1)

        count = await self.repo.count_user_uploads_between(
            user_id=user_id,
            start=today_start,
            end=tomorrow,
        )

        if count >= MAX_DAILY_UPLOADS:
            raise HTTPException(status_code=429, detail="Daily upload limit reached")

    async def get(self, profile_id: uuid.UUID, current_user):
        async def handler():
            profile = await self.repo.get_profile_by_user(
                profile_id=profile_id, user_id=current_user.id
            )
            cache_key = f"user_id:{current_user.id}:profile:{profile_id}"
            cached = await cache.get_json(cache_key)
            if cached:
                return self.mapper.one(cached, UserProfileSchemaOut)
            if not profile:
                raise HTTPException(status_code=404, detail="profile not found")

            profile_base = self.mapper.one(profile, UserProfileSchemaOut)

            await cache.set_json(
                cache_key, profile_base.model_dump(mode="json"), ttl=300
            )
            return profile_base

        return await breaker.call(handler)

    async def create(self, current_user, data):
        user_id = current_user.id
        await self.enforce_daily_quota(user_id=user_id)
        has_pic = await self.repo.has_profile_picture(user_id)

        if has_pic:
            raise HTTPException(
                status_code=400,
                detail="Profile picture already exists. Use update instead.",
            )

        profile_pic_hash = await self.compute.compute_file_hash(
            data.profile_pic_path,
        )

        if await self.repo.get_by_hash(user_id, profile_pic_hash):
            raise HTTPException(400, "This image has already been uploaded")
        profile_created = await self.repo.create(
            user_id=user_id,
            state_of_birth=data.state_of_birth,
            nin_verified=False,
            bvn_verified=False,
            nin_verified_at=None,
            bvn_verified_at=None,
            occupation=data.occupation,
            bvn_verification_provider=data.bvn_verification_provider,
            nin_verification_provider=data.nin_verification_provider,
            address=data.address,
            gender=data.gender,
            date_of_birth=data.date_of_birth,
            public_id=data.public_id,
            profile_pic_hash=profile_pic_hash,
            profile_pic_path=data.profile_pic_path,
            bvn_verification_status=BVNStatus.PENDING,
            nin_verification_status=NINVerificationStatus.PENDING,
        )
        #
        asyncio.create_task(
            self.fire_and_forget.profile_create(
                profile=profile_created, data=data, user_id=user_id
            )
        )
        return self.mapper.one(profile_created, UserProfileSchemaOut)

    async def _update_profile_pic_record(
        self,
        *,
        profile_id: uuid.UUID,
        user_id: uuid.UUID,
        profile_pic_path: str,
        profile_pic_hash: str,
        public_id: str,
        date_of_birth: date | None = None,
        gender: GenderChoices | None = None,
        address: str | None = None,
        occupation: str | None = None,
        state_of_birth: str | None = None,
    ):
        return await self.repo.update(
            user_id=user_id,
            profile_id=profile_id,
            new_profile_pic_path=profile_pic_path,
            new_profile_pic_hash=profile_pic_hash,
            new_public_id=public_id,
            new_date_of_birth=date_of_birth,
            new_gender=gender,
            new_state_of_birth=state_of_birth,
            new_occupation=occupation,
            new_address=address,
        )

    async def update(
        self, profile_id: uuid.UUID, current_user, data, resource_type: str = "images"
    ):
        async def handler():
            profile = await self.repo.get_profile_by_user(
                user_id=current_user.id, profile_id=profile_id
            )
            if not profile:
                raise HTTPException(status_code=404, detail="Profile not found")
            old_public_id = profile.public_id

            new_hash = await self.compute.compute_file_hash(
                data.profile_pic_path,
            )

            existing = await self.repo.get_by_hash(current_user.id, new_hash)
            if existing and existing.id != profile_id:
                raise HTTPException(
                    status_code=400,
                    detail="Another image with this content already exists",
                )

            updated = await self._update_profile_pic_record(
                user_id=current_user.id,
                profile_id=profile_id,
                profile_pic_path=data.profile_pic_path,
                profile_pic_hash=new_hash,
                public_id=data.public_id,
                date_of_birth=data.date_of_birth,
                gender=data.gender,
                state_of_birth=data.state_of_birth,
                occupation=data.occupation,
                address=data.address,
            )
            await self.repo.db_commit_and_refresh(updated)

            asyncio.create_task(
                self.fire_and_forget.profile_update(
                    public_id=old_public_id,
                    profile=updated,
                    current_user=current_user.id,
                    resource_type=resource_type,
                )
            )

            return self.mapper.one(updated, UserProfileSchemaOut)

        return await breaker.call(handler)

    async def delete(
        self,
        profile_id: uuid.UUID,
        current_user,
        idem_key: str,
        resource_type: str = "images",
    ):
        async def handler():
            existing_idem = await self.idem_repo.get(
                key=idem_key, user_id=current_user.id
            )
            if existing_idem and existing_idem.response:
                return existing_idem.response
            await self.idem_repo.save(idem_key, current_user.id, "DELETE:/profile")
            profile = await self.repo.get_profile_by_user(
                user_id=current_user.id, profile_id=profile_id
            )
            if not profile:
                raise HTTPException(404, "Profile not found")

            public_id = profile.public_id

            try:
                await self.repo.delete(current_user.id, profile_id)
                await self.repo.db_commit()

            except Exception:
                await self.repo.db_rollback()
                raise

            response = {
                "deleted": True,
                "profile_id": str(profile_id),
                "idem_key": idem_key,
            }
            asyncio.create_task(
                self.fire_and_forget.profile_delete(
                    public_id=public_id,
                    user_id=current_user.id,
                    profile_id=profile_id,
                    resource_type=resource_type,
                )
            )
            await self.idem_repo.store_response(
                key=idem_key, response=response, user_id=current_user.id
            )
            return response

        return await breaker.call(handler)
