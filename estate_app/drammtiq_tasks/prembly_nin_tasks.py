import uuid

import dramatiq

from core.get_db import AsyncSessionLocal
from models.enums import NINVerificationProviders
from security.security_verification import UserVerification


def create_prembly_nin_task():
    @dramatiq.actor(
        queue_name="verify_nin_prembly",
        max_retries=3,
        time_limit=600_000,
    )
    async def verify_nin(
        profile_id: uuid.UUID,
        nin: str,
    ):
        async with AsyncSessionLocal() as db:
            return await UserVerification(db).verify_nin(
                profile_id=profile_id,
                nin=nin,
                nin_verification_provider=NINVerificationProviders.PREMBLY,
            )

    return verify_nin
