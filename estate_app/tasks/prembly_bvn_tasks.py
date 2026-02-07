import logging
import uuid
from asyncio import run as async_run

import httpx

from celery import shared_task

from core.get_db import AsyncSessionLocal
from models.enums import BVNVerificationProviders
from services.verification_service import VerificationService

logger = logging.getLogger("bvn.prembly")


@shared_task(
    name="verify_bvn_prembly",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_prembly_bvn_task(profile_id: str, bvn: str):
    profile_uuid = uuid.UUID(profile_id)

    if not profile_uuid:
        raise ValueError("Invalid profile_id")
    async_run(verify_bvn(profile_uuid, bvn))
    return profile_uuid


async def verify_bvn(profile_id: uuid.UUID, bvn: str):
    async with AsyncSessionLocal() as db:
        return await VerificationService(db).verify_bvn(
            profile_id=profile_id,
            bvn=bvn,
            bvn_verification_provider=BVNVerificationProviders.PREMBLY,
        )


# def create_prembly_bvn_task(app):
#     class PremblyBVNTask(app.Task):
#         name = "verify_bvn_prembly"

#         autoretry_for = (ConnectionError, httpx.HTTPError, RuntimeError)
#         retry_backoff = True
#         retry_jitter = True
#         max_retries = 3
#         default_retry_delay = 10

#         async def _verify_bvn(
#             self,
#             profile_id: uuid.UUID,
#             bvn: str,
#         ):
#             async with AsyncSessionLocal() as db:
#                 return await UserVerification(db).verify_bvn(
#                     profile_id=profile_id,
#                     bvn=bvn,
#                     bvn_verification_provider=BVNVerificationProviders.PREMBLY,
#                 )

#         def run(self, profile_id: str, bvn: str):
#             profile_uuid = uuid.UUID(profile_id)
#             if not profile_uuid:
#                 raise ValueError("Invalid profile_id")
#             return asyncio_run.run_async(
#                 self._verify_bvn(
#                     profile_id=profile_uuid,
#                     bvn=bvn,
#                 )
#             )


#     return PremblyBVNTask
