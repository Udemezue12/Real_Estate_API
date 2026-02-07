import hashlib
import hmac
import re
import secrets
import uuid
from random import randint

from fastapi import Request
from itsdangerous import URLSafeTimedSerializer
from redis.asyncio import Redis

from core.breaker import breaker
from core.settings import settings

reset_serializer = URLSafeTimedSerializer(settings.RESET_SECRET_KEY)
verify_serializer = URLSafeTimedSerializer(settings.VERIFY_EMAIL_SECRET_KEY)

redis = Redis.from_url(settings.CELERY_REDIS_URL, decode_responses=True)


class UserGenerate:
    async def generate_reference(self):
        return str(uuid.uuid4().int)[:12]

    async def generate_unique_idem_key(
        self,
        request: Request,
    ) -> str:
        key = request.headers.get("Idempotency-Key")
        return key or str(uuid.uuid4())

    async def hmac_sha256(self, value: str, secret: str) -> str:
        return (
            hmac.new(
                key=secret.encode(),
                msg=value.encode(),
                digestmod=hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )

    async def generate_secure_public_id(
        self,
        prefix: str | None = None,
        length: int = 32,
    ):
        token = uuid.uuid4().hex[:length]

        token = re.sub(r"[^a-z0-9_-]", "_", token)

        if prefix:
            prefix = re.sub(r"[^a-z0-9_-]", "_", prefix.lower().strip("_"))
            return f"{prefix}_{token}"

        return token

    async def delete_token(self) -> str:
        return secrets.token_hex(32)

    async def generate_verify_token(self, email: str) -> str:
        return verify_serializer.dumps(email, salt=settings.VERIFY_EMAIL_SALT)

    async def generate_reset_token(self, email: str) -> str:
        return reset_serializer.dumps(email, salt=settings.RESET_PASSWORD_SALT)

    async def generate_otp(self, email: str) -> str:
        async def handler():
            otp = str(randint(100000, 999999))
            await redis.setex(f"otp:{email}", 300, otp)
            return otp

        return await breaker.call(handler)


user_generate = UserGenerate()
