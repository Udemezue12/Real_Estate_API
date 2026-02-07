import logging
import urllib.parse
import uuid
from typing import Awaitable, Callable

import httpx

from .breaker import breaker
from .settings import settings

logger = logging.getLogger(__name__)


class RedisIdempotency:
    def __init__(self, namespace: str = "idempotency"):
        redis_url = settings.UPSTASH_REDIS_URL
        if not redis_url:
            raise ValueError("Missing UPSTASH REDIS URL in the env variables")
        self.redis_url = redis_url.rstrip("/")
        self.redis_token = settings.UPSTASH_REDIS_TOKEN
        self.namespace = namespace

        if not self.redis_url or not self.redis_token:
            raise ValueError("Missing Upstash Redis environment variables")

        self.headers = {
            "Authorization": f"Bearer {self.redis_token}",
            "Content-Type": "application/json",
        }

    def _key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    async def acquire(self, key: str, ttl: int) -> bool:
        async def handler():
            encoded_key = urllib.parse.quote(self._key(key))
            token = uuid.uuid4().hex

            url = f"{self.redis_url}/set/{encoded_key}/{token}?EX={ttl}&NX"

            async with httpx.AsyncClient() as client:
                res = await client.post(
                    url,
                    headers=self.headers,
                )

                if res.status_code == 200 and res.json().get("result") == "OK":
                    return True

                if res.status_code == 200 and res.json().get("result") is None:
                    return False

                raise ConnectionError(f"Redis SET NX failed ({res.status_code})")

        return await breaker.call(handler)

    async def delete(self, key: str) -> bool:
        async def handler():
            encoded_key = urllib.parse.quote(self._key(key))

            url = f"{self.redis_url}/del/{encoded_key}"

            async with httpx.AsyncClient() as client:
                res = await client.post(
                    url,
                    headers=self.headers,
                )

                if res.status_code == 200:
                    return True

                raise ConnectionError(f"Redis DEL failed ({res.status_code})")

        return await breaker.call(handler)

    async def run_once(
        self,
        key: str,
        coro: Callable[[], Awaitable],
        ttl: int = 30,
    ):
        try:
            acquired = await self.acquire(key, ttl)
            if not acquired:
                raise RuntimeError("Duplicate request in progress or already processed")

            return await coro()
        finally:
            await self.delete(key)
