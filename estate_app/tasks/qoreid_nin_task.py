import logging
import uuid

import httpx


from celery import shared_task

from core.get_db import SyncSessionLocal
from models.enums import NINVerificationProviders
from services.verification_service import VerificationService

logger = logging.getLogger("nin.qoreid")


@shared_task(
    name="verify_nin_qoreid",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_qoreid_nin_task(profile_id: str, nin: str):
    profile_uuid = uuid.UUID(profile_id)

    if not profile_uuid:
        raise ValueError("Invalid profile_id")
    return verify_nin(profile_uuid, nin)


def verify_nin(profile_id: uuid.UUID, nin: str):
    db=SyncSessionLocal()
    try:
        return VerificationService(db).verify_nin(
            profile_id=profile_id,
            nin=nin,
            nin_verification_provider=NINVerificationProviders.QORE_ID,
        )
    except Exception:
        db.rollback()
    finally:
        db.close()


