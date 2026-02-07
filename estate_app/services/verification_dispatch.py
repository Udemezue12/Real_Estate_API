import logging
import uuid

from fastapi import HTTPException

from celery_worker.celery_app import app as task_app
from core.get_provider import ProviderResolver
from core.name_matcher import NameMatcher
from models.enums import (
    BVNStatus,
    NINVerificationStatus,
)
from repos.profile_repo import UserProfileRepo
from tasks.get_bvn_provider_tasks import GetBVNProvider
from tasks.get_nin_provider_tasks import GetNinProvider

logger = logging.getLogger("bvn.prembly")


class VerificationDispatch:
    def __init__(self, db):
        self.profile_repo = UserProfileRepo(db)
        self.provider = ProviderResolver()
        self.name_matcher = NameMatcher()

    async def reverify_bvn(self, *, profile_id: uuid.UUID, data):
        profile = await self.profile_repo.get_profile(profile_id)
        if profile.bvn_verification_status == BVNStatus.VERIFIED:
            raise HTTPException(status_code=409, detail="BVN already verified")
        bvn_provider = data.bvn_verification_provider
        bvn_task_name = GetBVNProvider.get_task_name(bvn_provider)
        task_app.send_task(bvn_task_name, args=[str(profile_id), str(data.bvn)])

    async def reverify_nin(self, *, profile_id: uuid.UUID, data):
        profile = await self.profile_repo.get_profile(profile_id)
        if profile.nin_verification_status == NINVerificationStatus.VERIFIED:
            raise HTTPException(status_code=409, detail="BVN already verified")
        nin_provider = data.nin_verification_provider
        nin_task_name = GetNinProvider.get_task_name(nin_provider)
        task_app.send_task(nin_task_name, args=[str(profile_id), str(data.bvn)])