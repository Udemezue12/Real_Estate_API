import asyncio
import base64
import json
import logging
import urllib.parse
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .breaker import breaker
from .settings import settings

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self):
        self.redis_url = settings.UPSTASH_REDIS_URL.rstrip("/")
        self.redis_token = settings.UPSTASH_REDIS_TOKEN

        if not self.redis_url or not self.redis_token:
            raise ValueError("Missing Upstash Redis environment variables")

        self.headers = {
            "Authorization": f"Bearer {self.redis_token}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def connect(self):
        async def handler():
            async with httpx.AsyncClient() as client:
                try:
                    logger.info("Connecting to Upstash Redis...")
                    res = await client.get(
                        f"{self.redis_url}/ping", headers=self.headers
                    )
                    if res.status_code == 200 and res.json().get("result") == "PONG":
                        logger.info("Connected to Upstash Redis.")
                    else:
                        raise ConnectionError("Upstash Redis ping failed.")
                except Exception as e:
                    logger.error("Redis connection error:", exc_info=e)
                    raise

        await breaker.call(handler)

    async def get(self, key: str) -> Optional[str]:
        async def handler():
            try:
                encoded_key = urllib.parse.quote(str(key))
                async with httpx.AsyncClient() as client:
                    res = await client.get(
                        f"{self.redis_url}/get/{encoded_key}", headers=self.headers
                    )
                    if res.status_code == 200:
                        return res.json().get("result")
                    if res.status_code == 404:
                        return None
                    raise ConnectionError(f"Redis GET failed ({res.status_code})")
            except httpx.RequestError as e:
                logger.error("Network error during Redis GET:", exc_info=e)
            except ConnectionError as e:
                logger.error("Connection error during Redis GET:", exc_info=e)
            except Exception as e:
                logger.error("Unexpected error during Redis GET:", exc_info=e)
            return None

        return await breaker.call(handler)

    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        if key is None or value is None:
            raise ValueError("Cache key and value cannot be None")

        async def handler():
            try:
                encoded_key = urllib.parse.quote(str(key))
                async with httpx.AsyncClient() as client:
                    url = f"{self.redis_url}/set/{encoded_key}?ex={ttl}"

                    res = await client.post(url, headers=self.headers, content=value)
                    if res.status_code == 200:
                        logger.debug("Cache set successfully for key: %s", key)
                        return
                    raise ConnectionError(f"Redis SET failed ({res.status_code})")
            except httpx.RequestError as e:
                logger.error("Network error during Redis SET:", exc_info=e)
            except ConnectionError as e:
                logger.error("Connection error during Redis SET:", exc_info=e)
            except Exception as e:
                logger.error("Unexpected error during Redis SET:", exc_info=e)

        return await breaker.call(handler)

    async def delete(self, key: str) -> bool:
        async def handler():
            try:
                encoded_key = urllib.parse.quote(str(key))
                async with httpx.AsyncClient() as client:
                    res = await client.post(
                        f"{self.redis_url}/del/{encoded_key}", headers=self.headers
                    )
                    if res.status_code == 200:
                        return True
                    return False
            except Exception as e:
                logger.error("Redis DELETE error:", exc_info=e)
                return False

        return await breaker.call(handler)

    async def get_json(self, key: str) -> Optional[Any]:
        data = await self.get(key)
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.error("Invalid JSON format in key: %s", key)
            return None

    async def set_json(self, key: str, value: Any, ttl: int = 3600) -> None:
        logger.debug("Setting JSON cache for key: %s", key)
        data = json.dumps(value)
        await self.set(key, data, ttl)
       

    def set_json_sync(self, key: str, value: Any):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(self.set_json(key, value))
        else:
            loop.run_until_complete(self.set_json(key, value))

    async def delete_cache_keys_async(self, *keys: str):
        if not keys:
            return
        unique_keys = set(keys)
        await asyncio.gather(*(self.delete(key) for key in unique_keys))

    async def get_raw(self, key: str) -> Optional[bytes]:
        data = await self.get(key)
        if not data:
            return None

        try:
            return base64.urlsafe_b64decode(data)
        except Exception as e:
            logger.error("Failed to decode raw cache value for key %s", key, exc_info=e)
            return None

    async def set_raw(self, key: str, value: bytes, ttl: int = 3600):
        if not isinstance(value, (bytes, bytearray)):
            raise TypeError("set_raw expects bytes")

        encoded = base64.urlsafe_b64encode(value).decode("ascii")
        await self.set(key, encoded, ttl)
        return {
            "key": key,
            "ttl": ttl,
            "size": len(encoded),
            "type": type(value).__name__,
        }

    async def delete_raw(self, key: str) -> bool:
        return await self.delete(key)

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.redis_url}/ping", headers=self.headers)
                return res.status_code == 200 and res.json().get("result") == "PONG"
        except Exception:
            return False


cache = Cache()
