

import dramatiq

from core.get_db import AsyncSessionLocal
from services.bank_service import BankService


def create_bank_name_tasks():
    @dramatiq.actor(
        queue_name="create_bank_names",
        max_retries=3,
        time_limit=600_000,
    )
    async def create():
            async with AsyncSessionLocal() as db:
                return await BankService(db).create()

    return create
