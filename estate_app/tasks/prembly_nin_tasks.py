
import logging
import uuid

import httpx
from asyncio import run as async_run

from celery import shared_task

from core.get_db import AsyncSessionLocal
from models.enums import NINVerificationProviders
from services.verification_service import VerificationService

logger = logging.getLogger("nin.prembly")


@shared_task(
    name="verify_nin_prembly",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_prembly_nin_task(profile_id: str, nin: str):
    profile_uuid = uuid.UUID(profile_id)

    if not profile_uuid:
        raise ValueError("Invalid profile_id")
    #
    return async_run(verify_nin(
        profile_id=profile_uuid,
        nin=nin,
    ))


async def verify_nin(profile_id: uuid.UUID, nin: str):
    async with AsyncSessionLocal() as db:
        return await VerificationService(db).verify_nin(
            profile_id=profile_id,
            nin=nin,
            nin_verification_provider=NINVerificationProviders.PREMBLY,
        )
