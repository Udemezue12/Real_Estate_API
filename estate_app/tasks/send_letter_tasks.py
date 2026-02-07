

import asyncio
import uuid

import httpx
from asgiref.sync import async_to_sync
from celery import shared_task

from core.get_db import AsyncSessionLocal
from repos.letters_repo import LetterRepo


@shared_task(
    name="send_bulk_letters",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)


def create_send_bulk_letter_tasks(
    property_id: str,
    letter_id: str,
    tenant_ids: list[str],
):
    letter_uuid = uuid.UUID(letter_id)
    property_uuid = uuid.UUID(property_id)

    tenant_uuids = []
    if tenant_ids:
        tenant_uuids = [uuid.UUID(tid) for tid in tenant_ids]

    return asyncio.run(
        send_bulk(letter_uuid, property_uuid, tenant_uuids)
    )



@shared_task(
    name="send_single_letter",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_send_single_letter_tasks(tenant_id: str, letter_id: str, property_id: str):
    return async_to_sync(send_single)(
        uuid.UUID(tenant_id),
        uuid.UUID(letter_id),
        uuid.UUID(property_id),
    )


async def send_bulk(
    letter_id: uuid.UUID,
    property_id: uuid.UUID,
    tenant_ids: list[uuid.UUID],
):
    async with AsyncSessionLocal() as db:
        repo = LetterRepo(db)

        return await repo.bulk_create_letter_recipient(
            property_id=property_id,
            letter_id=letter_id,
            tenant_ids=tenant_ids,
        )


async def send_single(
    tenant_id: uuid.UUID, letter_id: uuid.UUID, property_id: uuid.UUID
):
    async with AsyncSessionLocal() as db:
        return await LetterRepo(db).create_letter_recipient(
            tenant_id=tenant_id, property_id=property_id, letter_id=letter_id
        )
