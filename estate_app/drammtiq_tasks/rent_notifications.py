

import dramatiq

from core.get_db import AsyncSessionLocal
from services.rent_service import RentService


def create_rent_notification_task():
    @dramatiq.actor(
        queue_name="process_rent_notifications",
        max_retries=3,
        time_limit=600_000,
    )
    async def update_code():
        async with AsyncSessionLocal() as db:
            return await RentService(db).process_rent_notifications_using_celery()

    return update_code
