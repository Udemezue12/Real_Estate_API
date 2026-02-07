import uuid

import httpx
from asyncio import run as async_run
from celery import shared_task

from core.get_db import AsyncSessionLocal
from services.update_bank_codes import UpdateBankCodes


@shared_task(
    name="update_bank_code",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def update_bank_code_task( profile_id: str, user_input: str):
    profile_uuid = uuid.UUID(profile_id)

    if not profile_uuid:
        raise ValueError("Invalid profile_id")

    return async_run(update_code(profile_uuid, user_input))
    


async def update_code(profile_id: uuid.UUID, user_input: str):
    async with AsyncSessionLocal() as db:
        return await UpdateBankCodes(db).update_code(
            profile_id=profile_id, user_input=user_input
        )
