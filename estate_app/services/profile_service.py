import uuid
from datetime import date, datetime, timedelta, timezone

from celery import chain
from fastapi import HTTPException

from celery_worker.celery_app import app as task_app
from core.breaker import breaker
from core.cache import cache
from core.check_permission import CheckRolePermission
from core.cloudinary_setup import CloudinaryClient
from core.event_publish import publish_event
from core.file_hash import ComputeFileHash
from core.hash_and_update import AsyncioHashAndUpdate
from core.mapper import ORMMapper
from core.name_matcher import NameMatcher
from core.paginate import PaginatePage
from core.redis_idempotency import RedisIdempotency
from core.sensitive_hash import SensitiveHash
from fintechs.paystack import PaystackClient
from models.enums import (
    AccountNumberVerificationStatus,
    AccountVerificationProviders,
    BVNStatus,
    GenderChoices,
    NINVerificationStatus,
)
from repos.bank_repo import BankRepo
from repos.idempotency_repo import IdempotencyRepo
from repos.profile_repo import UserProfileRepo
from schemas.schema import UserProfileSchemaOut
from security.security_generate import UserGenerate
from tasks.get_bvn_provider_tasks import GetBVNProvider
from tasks.get_nin_provider_tasks import GetNinProvider

MAX_DAILY_UPLOADS = 1


class UserProfileService:
    CREATE_LOCK_KEY = "create-profile-v2"
    DELETE_LOCK_KEY = "delete-profile-v2"

    def __init__(self, db):
        self.bank_repo: BankRepo = BankRepo(db)
        self.mapper: ORMMapper = ORMMapper()
        self.paystack: PaystackClient = PaystackClient()
        self.repo: UserProfileRepo = UserProfileRepo(db)
        self.idem_repo: IdempotencyRepo = IdempotencyRepo(db)
        self.update_hash = AsyncioHashAndUpdate()
        self.cloudinary: CloudinaryClient = CloudinaryClient()
        self.name_matcher: NameMatcher = NameMatcher()
        self.paginate: PaginatePage = PaginatePage()
        self.sensitive_hash: SensitiveHash = SensitiveHash()
        self.generate: UserGenerate = UserGenerate()
        self.compute: ComputeFileHash = ComputeFileHash()
        self.permission: CheckRolePermission = CheckRolePermission()
        self.idempotency: RedisIdempotency = RedisIdempotency(namespace="user-profile")

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
            await self.permission.check_authenticated(current_user=current_user)
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
        async def _start():
            user_id = current_user.id
            await self.permission.check_authenticated(current_user=current_user)
            if await self.repo.get_by_user(user_id=user_id):
                raise HTTPException(400, "User profile already exists")
            await self.enforce_daily_quota(user_id=user_id)
            bank_name = await self.bank_repo.get_name(name=data.bank_name)
            if not bank_name:
                raise HTTPException(400, "Invalid bank name provided")
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
                paystack_account_verified=False,
                flutterwave_account_verified=False,
                bvn_verified=False,
                nin_verified_at=None,
                paystack_account_verified_at=None,
                flutterwave_account_verified_at=None,
                bvn_verified_at=None,
                occupation=data.occupation,
                bvn_verification_provider=data.bvn_verification_provider,
                paystack_account_verification_provider=AccountVerificationProviders.PAYSTACK,
                flutterwave_account_verification_provider=AccountVerificationProviders.FLUTTERWAVE,
                nin_verification_provider=data.nin_verification_provider,
                address=data.address,
                gender=data.gender,
                date_of_birth=data.date_of_birth,
                public_id=data.public_id,
                profile_pic_hash=profile_pic_hash,
                paystack_recipient_code=None,
                profile_pic_path=data.profile_pic_path,
                bvn_status=BVNStatus.PENDING,
                nin_verification_status=NINVerificationStatus.PENDING,
                bank_name=data.bank_name,
                paystack_account_verification_status=AccountNumberVerificationStatus.PENDING,
                flutterwave_account_verification_status=AccountNumberVerificationStatus.PENDING,
            )
            nin_provider = data.nin_verification_provider
            nin_task_name = GetNinProvider.get_task_name(nin_provider)
            bvn_provider = data.bvn_verification_provider
            bvn_task_name = GetBVNProvider.get_task_name(bvn_provider)

            chain(
                task_app.signature(
                    "update_bank_code",
                    args=[str(profile_created.id), str(profile_created.bank_name)],
                ),
                task_app.signature(
                    "verify_bank_account",
                    args=[str(profile_created.id), str(data.account_number)],
                    immutable=True,
                ),
                task_app.signature(
                    "get_receipient_code",
                    args=[str(profile_created.id)],
                    immutable=True,
                ),
                task_app.signature(
                    nin_task_name,
                    args=[str(profile_created.id), str(data.nin)],
                    immutable=True,
                ),
                task_app.signature(
                    bvn_task_name,
                    args=[str(profile_created.id), str(data.bvn)],
                    immutable=True,
                ),
            ).apply_async()

            await publish_event(
                "profile.created",
                {
                    "profile_id": str(profile_created.id),
                    "user_id": str(user_id),
                    "url": profile_created.profile_pic_path,
                },
            )

            return self.mapper.one(profile_created, UserProfileSchemaOut)

        return await self.idempotency.run_once(
            key=self.CREATE_LOCK_KEY,
            coro=_start,
            ttl=120,
        )

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
            await self.permission.check_authenticated(current_user=current_user)
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

            await self.cloudinary.safe_delete_cloudinary(
                public_id=old_public_id, resource_type=resource_type
            )
            await cache.delete_cache_keys_async(
                f"user_id:{current_user.id}:profile:{updated.id}"
            )
            await publish_event(
                "profile.updated",
                {
                    "profile_id": str(updated.id),
                    "user_id": str(current_user.id),
                    "url": updated.profile_pic_path,
                },
            )

            return self.mapper.one(updated, UserProfileSchemaOut)

        return await breaker.call(handler)

    async def delete(
        self,
        profile_id: uuid.UUID,
        current_user,
        
    ):
        async def _start():
            await self.permission.check_authenticated(current_user=current_user)
            profile = await self.repo.get_profile_by_user(
                user_id=current_user.id, profile_id=profile_id
            )
            if not profile:
                raise HTTPException(404, "Profile not found")

            public_id = profile.public_id

            await self.cloudinary.safe_delete_cloudinary(public_id, "images")
            try:
                await self.repo.delete(current_user.id, profile_id)
                await self.repo.db_commit()

            except Exception:
                await self.repo.db_rollback()
                raise


            await cache.delete_cache_keys_async(
                f"user_id:{current_user.id}:profile:{profile_id}"
            )

            return {
                "deleted": True,
                "profile_id": str(profile_id),
            }

        return await self.idempotency.run_once(
            key=self.DELETE_LOCK_KEY,
            coro=_start,
            ttl=120,
        )
