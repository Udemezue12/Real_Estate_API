import logging

import httpx
import asyncio
from celery import shared_task

from core.get_db import AsyncSessionLocal
from services.rent_service import RentService

logger = logging.getLogger("rent.notifications")



@shared_task(
    name="process_rent_notifications",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_rent_notification_task():
    return asyncio.run(process())


async def process():
    async with AsyncSessionLocal() as session:
        return await RentService(session).process_rent_notifications_using_celery()
