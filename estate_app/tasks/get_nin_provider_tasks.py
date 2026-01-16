import uuid

from celery_worker.celery_app import app as task_app
from models.enums import NINVerificationProviders


class GetNinProvider:
    def get_provider(self, profile_id: uuid.UUID, data):
        task_map = {
            NINVerificationProviders.QORE_ID: "verify_nin_qoreid",
            NINVerificationProviders.YOU_VERIFY: "verify_nin_youverify",
            NINVerificationProviders.PREMBLY: "verify_nin_prembly",
        }

        task_name = task_map.get(data.verification_provider)
        if not task_name:
            raise ValueError("Invalid verification provider")

        task_app.send_task(
            task_name,
            args=[str(profile_id), str(data.nin)],
        )
