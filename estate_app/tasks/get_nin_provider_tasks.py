from models.enums import NINVerificationProviders


class GetNinProvider:
    TASK_MAP = {
        NINVerificationProviders.QORE_ID: "verify_nin_qoreid",
        NINVerificationProviders.YOU_VERIFY: "verify_nin_youverify",
        NINVerificationProviders.PREMBLY: "verify_nin_prembly",
    }

    @classmethod
    def get_task_name(cls, provider):
        task_name = cls.TASK_MAP.get(provider)

        if not task_name:
            raise ValueError("Invalid verification provider")

        return task_name
