import uuid

from celery_worker.celery_app import app as task_app
from models.enums import BVNVerificationProviders


class GetBVNProvider:
    def get_provider(self, profile_id: uuid.UUID, data):
        task_map = {
            BVNVerificationProviders.QORE_ID: "verify_bvn_qoreid",
            BVNVerificationProviders.YOU_VERIFY: "verify_bvn_youverify",
            BVNVerificationProviders.PREMBLY: "verify_bvn_prembly",
        }

        task_name = task_map.get(data.bvn_verification_provider)
        if not task_name:
            raise ValueError("Invalid verification provider")

        task_app.send_task(
            task_name,
            args=[str(profile_id), str(data.bvn)],
        )
