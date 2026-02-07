import dramatiq

from core.get_db import AsyncSessionLocal
from services.expire_pending_conversation import ExpirePendingConverstaion


def create_rental_viewing_expiry_task():
    @dramatiq.actor(
        queue_name="expire_pending_rental_viewings",
        max_retries=3,
        time_limit=600_000,
    )
    async def expire_pending():
        async with AsyncSessionLocal() as session:
            return await ExpirePendingConverstaion(session).expire_pending_rentals()

    return expire_pending
