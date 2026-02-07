import uuid
from asyncio import run as async_run

import httpx

from celery import shared_task

from core.get_db import AsyncSessionLocal
from services.get_recipient_code_service import GetRecipientCode


@shared_task(
    name="get_receipient_code",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_receipient_code_task(profile_id: str):
    profile_uuid = uuid.UUID(profile_id)

    if not profile_uuid:
        raise ValueError("Invalid profile_id")
    async_run(get_code(profile_uuid))
    return profile_uuid


async def get_code(profile_id: uuid.UUID):
    async with AsyncSessionLocal() as db:
        return await GetRecipientCode(db).get_code(profile_id)


# def create_receipient_code_task(app):
#     class GetReceipientCodeTask(app.Task):
#         name = "get_receipient_code"

#         autoretry_for = (httpx.HTTPError, ConnectionError, RuntimeError)
#         retry_backoff = True
#         max_retries = 3

#         def run(self, profile_id: str):
#             profile_uuid = uuid.UUID(profile_id)

#             if not profile_uuid:
#                 raise ValueError("Invalid profile_id")
#             return asyncio_run.run_async(self._get_code(profile_uuid))

#         async def _get_code(self, profile_id: uuid.UUID):
#             async with AsyncSessionLocal() as db:
#                 return await GetRecipientCode(db).get_code(profile_id)


#     return GetReceipientCodeTask
