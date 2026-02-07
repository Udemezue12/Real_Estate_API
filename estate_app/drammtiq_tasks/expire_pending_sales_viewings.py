import dramatiq

from core.get_db import AsyncSessionLocal
from services.expire_pending_conversation import ExpirePendingConverstaion


def create_sales_viewing_expiry_task():
    @dramatiq.actor(
        queue_name="expire_pending_sales_viewings",
        max_retries=3,
        time_limit=600_000,
    )
    async def expire_pending():
        async with AsyncSessionLocal() as session:
            return await ExpirePendingConverstaion(session).expire_pending_sales()

    return expire_pending
