import uuid

import dramatiq

from core.get_db import AsyncSessionLocal
from services.get_recipient_code_service import GetRecipientCode


def create_receipient_code_task():
    @dramatiq.actor(
        queue_name="get_receipient_code",
        max_retries=3,
        time_limit=600_000,
    )
    async def get_code(profile_id: uuid.UUID):
            async with AsyncSessionLocal() as db:
                return await GetRecipientCode(db).get_code(profile_id)

    return get_code
