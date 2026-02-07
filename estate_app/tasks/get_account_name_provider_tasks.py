import uuid

from celery_worker.celery_app import app as task_app
from models.enums import AccountVerificationProviders


class GetAccountNameVerificationProvider:
    def get_provider(
        self,
        profile_id: uuid.UUID,
        data,
        
    ):
        # task_map = {
        #     AccountVerificationProviders.PAYSTACK: "verify_bank_account",
        # }

        # task_name = task_map.get(account_verification_provider)
        # if not task_name:
        #     raise ValueError("Invalid verification provider")

        task_app.send_task(
            "verify_bank_account",
            args=[str(profile_id), str(data.account_number)],
        )
