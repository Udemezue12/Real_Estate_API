import uuid
from asyncio import run as async_run

import httpx
from celery import shared_task

from core.get_db import AsyncSessionLocal
from services.account_name_match import AccountNameMatch


@shared_task(
    name="verify_bank_account",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_verify_account_tasks(profile_id: str, account_number: str):
    profile_uuid = uuid.UUID(profile_id)

    if not profile_uuid:
        raise ValueError("Invalid profile_id")
    return async_run(match_name(profile_uuid, account_number))
    


async def match_name(profile_id: uuid.UUID, account_number: str):
    async with AsyncSessionLocal() as db:
        return await AccountNameMatch(db).match_name(
            profile_id=profile_id, account_number=account_number
        )
