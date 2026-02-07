import logging

import httpx
from asyncio import run as async_run

from celery import shared_task

from core.get_db import AsyncSessionLocal
from services.bank_service import BankService

logger = logging.getLogger("bank_names")


@shared_task(
    name="create_bank_names",
    autoretry_for=(httpx.HTTPError, ConnectionError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_bank_name_tasks():
    return async_run(create())


async def create():
    async with AsyncSessionLocal() as db:
        return await BankService(db).create()


