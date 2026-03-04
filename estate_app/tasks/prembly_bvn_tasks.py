import logging
import uuid


import httpx

from celery import shared_task

from core.get_db import SyncSessionLocal
from models.enums import BVNVerificationProviders
from services.verification_service import VerificationService

logger = logging.getLogger("bvn.prembly")


@shared_task(
    name="verify_bvn_prembly",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def create_prembly_bvn_task(profile_id: str, bvn: str):
    profile_uuid = uuid.UUID(profile_id)

    if not profile_uuid:
        raise ValueError("Invalid profile_id")
    return verify_bvn(profile_uuid, bvn)


def verify_bvn(profile_id: uuid.UUID, bvn: str):
    db = SyncSessionLocal()
    try:
        return VerificationService(db).verify_bvn(
            profile_id=profile_id,
            bvn=bvn,
            bvn_verification_provider=BVNVerificationProviders.PREMBLY,
        )
    except:
        db.rollback()
    finally:
        db.close()
