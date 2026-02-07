import uuid

import dramatiq

from core.get_db import AsyncSessionLocal
from models.enums import BVNVerificationProviders
from security.security_verification import UserVerification


def create_prembly_bvn_task():
    @dramatiq.actor(
        queue_name="verify_bvn_prembly",
        max_retries=3,
        time_limit=600_000,
    )
    async def verify_bvn(
        profile_id: uuid.UUID,
        bvn: str,
    ):
        async with AsyncSessionLocal() as db:
            return await UserVerification(db).verify_bvn(
                profile_id=profile_id,
                bvn=bvn,
                bvn_verification_provider=BVNVerificationProviders.PREMBLY,
            )

    return verify_bvn
