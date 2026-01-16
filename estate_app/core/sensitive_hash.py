import hashlib
from core.settings import settings
from fastapi import HTTPException


class SensitiveHash:
    @staticmethod
    async def hash_nin(nin: str) -> str:
        if not settings.SECRET_KEY:
            raise HTTPException(404, "Secret key Not Found")

        normalized = nin.strip().encode()
        salted = settings.SECRET_KEY.encode() + normalized
        return hashlib.sha256(salted).hexdigest()
