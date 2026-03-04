
import httpx
from celery import shared_task

from core.get_db import SyncSessionLocal
from services.expire_pending_conversation import ExpirePendingConverstaion


@shared_task(
    name="expire_pending_sales_viewings",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_sales_viewing_expiry_task():
    return expire_pending()


def expire_pending():
    session = SyncSessionLocal()
    try:
        return ExpirePendingConverstaion(session).expire_pending_sales()
    except Exception:

        session.rollback()
    finally:
        session.close()
