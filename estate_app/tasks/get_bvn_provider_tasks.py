from models.enums import BVNVerificationProviders


class GetBVNProvider:
    TASK_MAP = {
        BVNVerificationProviders.QORE_ID: "verify_bvn_qoreid",
        BVNVerificationProviders.YOU_VERIFY: "verify_bvn_youverify",
        BVNVerificationProviders.PREMBLY: "verify_bvn_prembly",
    }

    @classmethod
    def get_task_name(cls, provider):
        task_name = cls.TASK_MAP.get(provider)

        if not task_name:
            raise ValueError("Invalid verification provider")

        return task_name
    
