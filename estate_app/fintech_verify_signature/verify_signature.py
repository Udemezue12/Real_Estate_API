import hmac
import hashlib
from core.settings import settings


class FintechsVerifySignature:

    @staticmethod
    def verify_paystack_signature(signature: str, body: bytes) -> bool:

        if not signature:
            return False

        secret = settings.PAYSTACK_SECRET_KEY.encode()

        expected = hmac.new(
            secret,
            body,
            hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(expected, signature)
    @staticmethod
    def verify_flutterwave_signature(signature: str, body: bytes) -> bool:

        if not signature:
            return False

        secret = settings.FLUTTERWAVE_WEBHOOK_SECRET.encode()

        expected = hmac.new(
            secret,
            body,
            hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(expected, signature)
