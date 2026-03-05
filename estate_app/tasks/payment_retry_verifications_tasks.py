import httpx
from celery import shared_task
from core.get_db import SyncSessionLocal
from services.retry_payment_verification import PaymentRetry


@shared_task(
    name="retry_verify_payment",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def retry_payment_tasks(reference: str):
    try:
        updated = retry_payment(reference)
        return updated
    except Exception:
        raise


def retry_payment(reference: str):
    db = SyncSessionLocal()
    try:
        return PaymentRetry(db).run_retry(reference)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close_all()