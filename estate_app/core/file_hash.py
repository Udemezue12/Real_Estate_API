import asyncio
import hashlib

import aiohttp
import requests
from fastapi import HTTPException

from core.asyncio_threads import AsyncioBaseService


class ComputeFileHash:
    def __init__(self):
        self.asyncio_threads = AsyncioBaseService()

    async def compute_file_hash_async(self, file_url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=400, detail="Failed to fetch file")

                content = await resp.read()
                return hashlib.sha256(content).hexdigest()

    def compute_file_hash_sync(self, file_url: str) -> str:
        try:
            resp = requests.get(file_url, timeout=30)
        except requests.RequestException:
            raise HTTPException(status_code=400, detail="Failed to fetch file")

        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch file")

        return hashlib.sha256(resp.content).hexdigest()

    async def compute_file_hash(self, file_url: str, executor=None) -> str:
        try:
            return await self.asyncio_threads.run_blocking(
                self.compute_file_hash_sync,
                file_url,
                executor=executor,
            )
        except HTTPException:
            raise
        except asyncio.CancelledError:
            raise
        except Exception:
            return await self.compute_file_hash_async(file_url)
