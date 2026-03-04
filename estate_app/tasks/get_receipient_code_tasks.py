import uuid
from asyncio import run as async_run

import httpx

from celery import shared_task

from core.get_db import SyncSessionLocal
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
    return get_code(profile_uuid)


def get_code(profile_id: uuid.UUID):
    db = SyncSessionLocal()
    try:
        return GetRecipientCode(db).get_code(profile_id)
    except Exception:
        db.rollback()
    finally:
        db.close()
