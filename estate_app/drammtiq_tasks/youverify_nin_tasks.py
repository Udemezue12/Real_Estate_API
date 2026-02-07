import uuid

import dramatiq

from core.get_db import AsyncSessionLocal
from models.enums import BVNVerificationProviders
from security.security_verification import UserVerification


def create_youverify_nin_task():
    @dramatiq.actor(
        queue_name="verify_bvn_youverify",
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
                bvn_verification_provider=BVNVerificationProviders.YOU_VERIFY,
            )

    return verify_nin
