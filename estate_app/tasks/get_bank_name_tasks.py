import logging

import httpx


from celery import shared_task

from core.get_db import SyncSessionLocal
from services.bank_service import BankService

logger = logging.getLogger("bank_names")


@shared_task(
    name="create_bank_names",
    autoretry_for=(httpx.HTTPError, ConnectionError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_bank_name_tasks():
    return create()


def create():
    db = SyncSessionLocal()
    try:

        return BankService(db).create()
    except Exception:
        db.rollback()
    finally:
        db.close()
