import logging
import uuid

import asyncio


import httpx
from celery import shared_task

from core.get_db import AsyncSessionLocal
from models.enums import NINVerificationProviders
from services.verification_service import VerificationService
logger = logging.getLogger("nin.youverify")


@shared_task(
    name="verify_nin_youverify",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_youverify_nin_task(profile_id: str, nin: str):
    profile_uuid = uuid.UUID(profile_id)

    if not profile_uuid:
        raise ValueError("Invalid profile_id")
    return asyncio.run(verify_nin(profile_uuid, nin))


async def verify_nin(profile_id: uuid.UUID, nin: str):
    async with AsyncSessionLocal() as db:
        return await VerificationService(db).verify_nin(
            profile_id=profile_id,
            nin=nin,
            nin_verification_provider=NINVerificationProviders.YOU_VERIFY,
        )
