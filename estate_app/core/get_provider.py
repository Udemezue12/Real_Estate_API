from models.enums import BVNVerificationProviders, NINVerificationProviders
from verify_nin.verify_nin_permbly import PremblyNINVerifier
from verify_nin.verify_nin_qoreID import QoreIDVerifyyNin
from verify_nin.verify_nin_youVerify import YouVerifyNin


class ProviderResolver:
    def __init__(self):
        self.nin_providers = {
            NINVerificationProviders.PREMBLY: PremblyNINVerifier(),
            NINVerificationProviders.QORE_ID: QoreIDVerifyyNin(),
            NINVerificationProviders.YOU_VERIFY: YouVerifyNin(),
        }
        self.bvn_providers = {
            BVNVerificationProviders.PREMBLY,
            BVNVerificationProviders.QORE_ID,
            BVNVerificationProviders.YOU_VERIFY,
        }

    def get_nin(self, provider: NINVerificationProviders):
        return self.nin_providers[provider]

    def get_bvn(self, provider: BVNVerificationProviders):
        return self.bvn_providers[provider]
