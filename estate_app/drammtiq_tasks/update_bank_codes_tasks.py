import uuid

import dramatiq

from core.get_db import AsyncSessionLocal
from services.update_bank_codes import UpdateBankCodes


def update_bank_code_task():
    @dramatiq.actor(
        queue_name="update_bank_code",
        max_retries=3,
        time_limit=600_000,
    )
    async def update_code(
        profile_id: uuid.UUID,
        user_input: str,
    ):
        async with AsyncSessionLocal() as db:
            return await UpdateBankCodes(db).update_code(
                profile_id=profile_id, user_input=user_input
            )

    return update_code
