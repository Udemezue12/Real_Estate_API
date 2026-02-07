import uuid

import dramatiq

from core.get_db import AsyncSessionLocal
from services.account_name_match import AccountNameMatch


def create_verify_account_task():
    @dramatiq.actor(
        queue_name="verify_bank_account",
        max_retries=3,
        time_limit=600_000,
    )
    async def name_match( profile_id: uuid.UUID, account_number: str):
        async with AsyncSessionLocal() as session:
            return await AccountNameMatch(session).match_name(
                profile_id=profile_id, account_number=account_number
            )

    return name_match
