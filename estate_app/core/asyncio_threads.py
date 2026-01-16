import asyncio
from typing import Callable, Any


class BaseService:
    async def run_blocking(
        self,
        func: Callable[..., Any],
        *args,
        executor=None,
    ) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, func, *args)
