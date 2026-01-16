
import hmac
import hashlib
import time
from .settings import settings


class DeleteTokenGenerator:
    SECRET_KEY = (settings.SECRET_KEY or "").encode("utf-8")


    @classmethod
    async def generate_token(cls, image_id: str, expires_in: int = 300) -> str:
        expiry: int = int(time.time()) + expires_in
        message = f"{image_id}:{expiry}".encode("utf-8")
        digest: str = hmac.new(cls.SECRET_KEY, message, hashlib.sha256).hexdigest()
        return f"{digest}:{expiry}"

    @classmethod
    async def validate_token(cls, image_id: str, token: str) -> bool:
        try:
            digest, expiry_str = token.split(":")
            expiry: int = int(expiry_str)
        except ValueError:
            return False

        if time.time() > expiry:
            return False

        message = f"{image_id}:{expiry}".encode("utf-8")
        expected_digest: str = hmac.new(
            cls.SECRET_KEY, message, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_digest, digest)
