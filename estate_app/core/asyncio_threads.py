import asyncio
from typing import Callable, Any


class AsyncioBaseService:
    async def run_blocking(
        self,
        func: Callable[..., Any],
        *args,
        executor=None,
    ) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, func, *args)

    def run_async_event(self, coro):
        loop = asyncio.new_event_loop()

        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                asyncio.set_event_loop(None)
                loop.close()

    def run_async(self, coro):
        return asyncio.run(coro)


asyncio_run = AsyncioBaseService()
