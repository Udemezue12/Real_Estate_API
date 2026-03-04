
from datetime import datetime, timedelta, timezone

import httpx
from celery import shared_task
from core.get_db import SyncSessionLocal
from repos.auth_repo import AuthRepo


@shared_task(
    name="delete_blackisted_tokens",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def delete():
    db = SyncSessionLocal()
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    try:
        return AuthRepo(db).sync_delete_expired_blacklisted_tokens(cutoff)

    except Exception:
        db.rollback()
    finally:
        db.close()
